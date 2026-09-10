import os, asyncio, uuid, glob, random
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import aiofiles

from data import TEST_CASES, tune_for_rime
from tts.providers import get_provider, PROVIDERS_CONFIG, RELIABILITY_STATS
from db import init_db, save_mos_rating, export_mos_csv_string
from dotenv import load_dotenv
import uvicorn
import jiwer
from asr import transcribe_audio, MODEL_SIZE, COMPUTE_TYPE, EVAL_BEAM_SIZE
from epitran import Epitran

load_dotenv()

RIME_API_KEY = os.getenv("RIME_API_KEY")
if not RIME_API_KEY:
    raise RuntimeError("RIME_API_KEY environment variable is missing or empty. Please set it in .env")

app = FastAPI(title="RimeRx Voice Safety API")
app.mount("/static", StaticFiles(directory="static"), name="static")
AUDIO_DIR = "static/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# --- STARTUP CLEANUP: KEEP ONLY LAST 50 AUDIO CLIPS ---
def cleanup_audio_dir(directory: str = AUDIO_DIR, max_files: int = 50):
    files = glob.glob(os.path.join(directory, "*.mp3"))
    if len(files) > max_files:
        files.sort(key=os.path.getctime)
        files_to_delete = files[:-max_files]
        for f in files_to_delete:
            try:
                os.remove(f)
            except Exception:
                pass

cleanup_audio_dir()
init_db()

# --- IN-MEMORY BLIND TEST SESSION STORE ---
BLIND_SESSIONS = {}

from typing import Optional

class RenderRequest(BaseModel):
    case_id: Optional[str] = None
    custom_text: Optional[str] = None
    prompt_type: str = "default" # "default" | "tuned"
    provider: Optional[str] = "rime"

class WerRequest(BaseModel):
    audio_id: str
    case_id: Optional[str] = None
    custom_text: Optional[str] = None
    prompt_type: Optional[str] = "default"
    provider: Optional[str] = "rime"

class MosRatingRequest(BaseModel):
    session_id: str
    target: str # "A" | "B"
    naturalness: int = Field(..., ge=1, le=5)
    intelligibility: int = Field(..., ge=1, le=5)

def get_target_case(req):
    if req.case_id:
        case = next((c for c in TEST_CASES if c["id"] == req.case_id), None)
        if case: return case
    if req.custom_text:
        return {
            "id": "custom",
            "domain": "Custom Prescription",
            "raw_text": req.custom_text,
            "expected_pronunciation": tune_for_rime(req.custom_text)
        }
    raise HTTPException(400, "Must provide case_id or custom_text")

@app.get("/", response_class=HTMLResponse)
async def index():
    async with aiofiles.open("static/index.html", mode="r", encoding="utf-8") as f:
        content = await f.read()
    return content

@app.get("/api/config")
async def get_config():
    return {
        "per_threshold": 5.0,
        "max_text_length": 2500,
        "model_id": "mist/v1",
        "voice": "marsh",
        "language": "en-IN",
        "providers": PROVIDERS_CONFIG
    }

@app.get("/api/reliability")
async def get_reliability():
    return RELIABILITY_STATS

@app.get("/api/cases")
async def get_cases():
    return [
        {
            "id": c["id"],
            "domain": c["domain"],
            "text": c["raw_text"],
            "is_edge_case": c.get("is_edge_case", False)
        }
        for c in TEST_CASES
    ]

@app.post("/api/render")
async def render_audio(req: RenderRequest):
    case = get_target_case(req)

    text = case["raw_text"] if req.prompt_type == "default" else tune_for_rime(case["raw_text"])

    # Reject text exceeding 2500 characters
    if len(text) > 2500:
        raise HTTPException(400, "Text exceeds maximum benchmark limit of 2500 characters")

    provider_name = req.provider.lower() if req.provider else "rime"
    tts_provider = get_provider(provider_name)

    audio_bytes, meta = await tts_provider.synthesize(text)

    file_prefix = req.case_id if req.case_id else "custom"
    fname = f"{file_prefix}_{provider_name}_{req.prompt_type}_{uuid.uuid4().hex[:4]}.mp3"
    fpath = os.path.join(AUDIO_DIR, fname)

    async with aiofiles.open(fpath, "wb") as f:
        await f.write(audio_bytes)

    return {
        "audio_id": fname,
        "audio_url": f"/static/audio/{fname}",
        "prompt_used": text,
        "provider": meta["provider"],
        "model": meta["model"],
        "voice": meta["voice"],
        "language": meta["language"],
        "ttfb_ms": meta.get("ttfb_ms"),
        "total_ms": meta.get("total_ms"),
        "cold": meta.get("cold"),
        "notes": meta.get("notes", "")
    }

# --- BLIND MOS COMPARISON ENDPOINTS ---
@app.post("/api/blind/session")
async def create_blind_session():
    """Generates a blinded comparison session picking a random case and two anonymized provider renders."""
    case = random.choice(TEST_CASES)
    provider_options = ["rime", "openai", "elevenlabs"]
    
    # Pick two distinct providers or configurations
    p_a_name, p_b_name = random.sample(provider_options, 2)
    
    p_a = get_provider(p_a_name)
    p_b = get_provider(p_b_name)

    text = tune_for_rime(case["raw_text"])

    try:
        bytes_a, meta_a = await p_a.synthesize(text)
        bytes_b, meta_b = await p_b.synthesize(text)
    except Exception:
        # Fallback if alternative API key missing
        bytes_a, meta_a = await get_provider("rime").synthesize(case["raw_text"])
        bytes_b, meta_b = await get_provider("rime").synthesize(text)
        p_a_name, p_b_name = "rime_default", "rime_tuned"

    fname_a = f"blind_A_{uuid.uuid4().hex[:4]}.mp3"
    fname_b = f"blind_B_{uuid.uuid4().hex[:4]}.mp3"

    fpath_a = os.path.join(AUDIO_DIR, fname_a)
    fpath_b = os.path.join(AUDIO_DIR, fname_b)

    async with aiofiles.open(fpath_a, "wb") as f:
        await f.write(bytes_a)
    async with aiofiles.open(fpath_b, "wb") as f:
        await f.write(bytes_b)

    session_id = f"blind_{uuid.uuid4().hex[:8]}"
    BLIND_SESSIONS[session_id] = {
        "case_id": case["id"],
        "raw_text": case["raw_text"],
        "A": {"provider": p_a_name, "variant": "tuned" if "tuned" in p_a_name else "default", "audio_id": fname_a},
        "B": {"provider": p_b_name, "variant": "tuned" if "tuned" in p_b_name else "default", "audio_id": fname_b}
    }

    return {
        "session_id": session_id,
        "case_id": case["id"],
        "raw_text": case["raw_text"],
        "audio_a_url": f"/static/audio/{fname_a}",
        "audio_b_url": f"/static/audio/{fname_b}"
    }

@app.post("/api/mos")
async def submit_mos_rating(req: MosRatingRequest):
    session = BLIND_SESSIONS.get(req.session_id)
    if not session:
        raise HTTPException(404, "Invalid or expired blind evaluation session_id")

    target_key = req.target.upper()
    if target_key not in ("A", "B"):
        raise HTTPException(400, "Target must be 'A' or 'B'")

    target_meta = session[target_key]
    provider_name = target_meta["provider"]
    variant = target_meta["variant"]
    case_id = session["case_id"]

    save_mos_rating(
        session_id=req.session_id,
        case_id=case_id,
        provider=provider_name,
        variant=variant,
        naturalness=req.naturalness,
        intelligibility=req.intelligibility
    )

    return {
        "message": "MOS rating recorded successfully",
        "session_id": req.session_id,
        "target": target_key,
        "revealed_provider": provider_name,
        "revealed_variant": variant,
        "naturalness": req.naturalness,
        "intelligibility": req.intelligibility
    }

@app.get("/api/mos/export")
async def export_mos_ratings():
    csv_data = export_mos_csv_string()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mos_ratings.csv"}
    )

# --- METRICS ENDPOINT ---
epi = Epitran('eng-Latn') # English G2P

def text_to_phonemes(text):
    words = text.lower().split()
    phonemes = []
    for w in words:
        try:
            p = epi.transliterate(w)
            phonemes.append(p if p else w)
        except Exception:
            phonemes.append(w)
    return " ".join(phonemes)

def analyze_word_errors(reference: str, hypothesis: str):
    ref_clean = reference.lower().replace('.', '').replace(',', '')
    hyp_clean = hypothesis.lower().replace('.', '').replace(',', '')

    out = jiwer.process_words(ref_clean, hyp_clean)
    hyp_words = hypothesis.split()
    word_details = []

    if out.alignments:
        alignments = out.alignments[0]
        hyp_status = {}
        for chunk in alignments:
            for idx in range(chunk.hyp_start_idx, chunk.hyp_end_idx):
                hyp_status[idx] = chunk.type
        for idx, word in enumerate(hyp_words):
            status = hyp_status.get(idx, 'equal')
            word_details.append({
                'word': word,
                'error': status != 'equal',
                'type': status
            })
    else:
        for word in hyp_words:
            word_details.append({'word': word, 'error': False, 'type': 'equal'})

    wer_percent = round(out.wer * 100, 2)
    return wer_percent, word_details

@app.post("/api/evaluate")
async def evaluate(req: RenderRequest):
    case = get_target_case(req)

    prompt_text = case["raw_text"] if req.prompt_type == "default" else tune_for_rime(case["raw_text"])
    expected_text = case["expected_pronunciation"]

    pred_phonemes = text_to_phonemes(prompt_text)
    ref_phonemes = text_to_phonemes(expected_text)

    per = jiwer.wer(ref_phonemes, pred_phonemes) # Phoneme Error Rate
    cer_score = jiwer.cer(ref_phonemes, pred_phonemes)

    return {
        "prompt_used": prompt_text,
        "expected_pronunciation": expected_text,
        "pred_phonemes": pred_phonemes,
        "ref_phonemes": ref_phonemes,
        "PER": round(per * 100, 2),
        "CER": round(cer_score * 100, 2),
        "note": "Metric compares Prompt Phonemes vs Gold Phonemes. True WER requires ASR on audio."
    }

@app.post("/api/wer")
async def calculate_true_wer(req: WerRequest):
    if not req.audio_id:
        raise HTTPException(400, "audio_id parameter is required")

    filename = os.path.basename(req.audio_id)
    audio_path = os.path.join(AUDIO_DIR, filename)

    if not os.path.exists(audio_path):
        raise HTTPException(404, f"Audio file '{filename}' not found. Click 'Listen' first.")

    case = get_target_case(req)
    reference = case["expected_pronunciation"]

    loop = asyncio.get_running_loop()
    hypothesis = await loop.run_in_executor(None, transcribe_audio, audio_path, EVAL_BEAM_SIZE)

    wer_score, word_details = analyze_word_errors(reference, hypothesis)

    return {
        "audio_id": filename,
        "audio_file": f"/static/audio/{filename}",
        "reference": reference,
        "hypothesis": hypothesis,
        "words": word_details,
        "WER": wer_score,
        "note": f"ASR Model: {MODEL_SIZE} ({COMPUTE_TYPE}, beam_size={EVAL_BEAM_SIZE})"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
