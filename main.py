import os
os.environ["PYTHONUTF8"] = "1"
import asyncio, uuid, glob, random
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import aiofiles

from data import TEST_CASES, STRESS_TEST_CASES, tune_for_rime, safe_tune_for_rime, extract_critical_entities, validate_semantic_preservation, evaluate_stress_case
from tts.providers import get_provider, PROVIDERS_CONFIG, RELIABILITY_STATS
from db import init_db, save_mos_rating, export_mos_csv_string
from config.rime import RIME_MODEL, RIME_SPEAKER, RIME_LANGUAGE
from dotenv import load_dotenv
import uvicorn
import jiwer
from asr import transcribe_audio, verify_critical_entities, MODEL_SIZE, COMPUTE_TYPE, EVAL_BEAM_SIZE
try:
    from epitran import Epitran
except Exception:
    Epitran = None
load_dotenv()

RIME_API_KEY = os.getenv("RIME_API_KEY")
if not RIME_API_KEY:
    print("[WARNING] RIME_API_KEY environment variable is missing or empty. Please configure it in Render/environment variables.", flush=True)

app = FastAPI(title="RimeRx Voice Safety API")
app.mount("/static", StaticFiles(directory="static"), name="static")
AUDIO_DIR = "static/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

@app.get("/health")
@app.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "RimeRx"}

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
    medication_correct: Optional[bool] = None
    strength_correct: Optional[bool] = None
    dosage_correct: Optional[bool] = None
    duration_correct: Optional[bool] = None
    date_correct: Optional[bool] = None

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
        "model_id": RIME_MODEL,
        "voice": RIME_SPEAKER,
        "language": RIME_LANGUAGE,
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

    if req.prompt_type == "default":
        text = case["raw_text"]
        safety_meta = {"is_safe": True}
    else:
        safety_res = safe_tune_for_rime(case["raw_text"])
        text = safety_res["prompt_used"]
        safety_meta = safety_res

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
        "safety": safety_meta,
        "notes": meta.get("notes", "")
    }

# --- BLIND MOS COMPARISON ENDPOINTS ---
@app.post("/api/blind/session")
async def create_blind_session():
    """Generates a blinded comparison session evaluating Rime default vs. tuned output for a random case."""
    case = random.choice(TEST_CASES)
    rime_provider = get_provider("rime")

    raw_text = case["raw_text"]
    tuned_text = tune_for_rime(raw_text)

    bytes_default, _ = await rime_provider.synthesize(raw_text)
    bytes_tuned, _ = await rime_provider.synthesize(tuned_text)

    options = [("default", bytes_default), ("tuned", bytes_tuned)]
    random.shuffle(options)

    (variant_a, bytes_a), (variant_b, bytes_b) = options

    fname_a = f"blind_A_{uuid.uuid4().hex[:4]}.mp3"
    fname_b = f"blind_B_{uuid.uuid4().hex[:4]}.mp3"

    fpath_a = os.path.join(AUDIO_DIR, fname_a)
    fpath_b = os.path.join(AUDIO_DIR, fname_b)

    async with aiofiles.open(fpath_a, "wb") as f:
        await f.write(bytes_a)
    async with aiofiles.open(fpath_b, "wb") as f:
        await f.write(bytes_b)

    critical_entities = extract_critical_entities(case["raw_text"])

    session_id = f"blind_{uuid.uuid4().hex[:8]}"
    BLIND_SESSIONS[session_id] = {
        "case_id": case["id"],
        "raw_text": case["raw_text"],
        "critical_entities": critical_entities,
        "A": {"provider": "rime", "variant": variant_a, "audio_id": fname_a},
        "B": {"provider": "rime", "variant": variant_b, "audio_id": fname_b}
    }

    return {
        "session_id": session_id,
        "case_id": case["id"],
        "raw_text": case["raw_text"],
        "critical_entities": critical_entities,
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
        intelligibility=req.intelligibility,
        medication_correct=req.medication_correct,
        strength_correct=req.strength_correct,
        dosage_correct=req.dosage_correct,
        duration_correct=req.duration_correct,
        date_correct=req.date_correct
    )

    return {
        "message": "MOS rating recorded successfully",
        "session_id": req.session_id,
        "target": target_key,
        "revealed_provider": provider_name,
        "revealed_variant": variant,
        "naturalness": req.naturalness,
        "intelligibility": req.intelligibility,
        "comprehension": {
            "medication_correct": req.medication_correct,
            "strength_correct": req.strength_correct,
            "dosage_correct": req.dosage_correct,
            "duration_correct": req.duration_correct,
            "date_correct": req.date_correct
        }
    }

@app.get("/api/mos/export")
async def export_mos_ratings():
    csv_data = export_mos_csv_string()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mos_ratings.csv"}
    )

# --- STRESS TEST SYSTEM ENDPOINTS (PHASE 9) ---
class StressRunRequest(BaseModel):
    case_id: Optional[str] = None
    provider: Optional[str] = "rime"

@app.get("/api/stress/cases")
async def get_stress_cases():
    """Returns all dedicated stress test cases with difficulty labels and expected pronunciations."""
    return STRESS_TEST_CASES

@app.post("/api/stress/run")
async def run_stress_test(req: StressRunRequest):
    """
    Executes a dedicated stress-test run for a target case ID.
    Renders Rime baseline vs RimeRx tuned speech, transcribes with ASR,
    and performs honest per-entity matching (drug, strength, dose, frequency, duration, date)
    with explicit failure limitation notes when misheard.
    """
    case = None
    if req.case_id:
        case = next((c for c in STRESS_TEST_CASES if c["id"] == req.case_id), None)
        if not case:
            case = next((c for c in TEST_CASES if c["id"] == req.case_id), None)
    if not case:
        case = STRESS_TEST_CASES[0]

    raw_text = case["raw_text"]
    provider_name = req.provider or "rime"
    provider = get_provider(provider_name)

    # 1. Synthesize baseline audio
    baseline_bytes, meta_base = await provider.synthesize(raw_text)
    fname_base = f"stress_{case['id']}_{provider_name}_base_{uuid.uuid4().hex[:4]}.mp3"
    fpath_base = os.path.join(AUDIO_DIR, fname_base)
    async with aiofiles.open(fpath_base, "wb") as f:
        await f.write(baseline_bytes)

    # 2. Synthesize safety-tuned audio
    tuned_meta = safe_tune_for_rime(raw_text)
    tuned_prompt = tuned_meta["prompt_used"]
    tuned_bytes, meta_tuned = await provider.synthesize(tuned_prompt)
    fname_tuned = f"stress_{case['id']}_{provider_name}_tuned_{uuid.uuid4().hex[:4]}.mp3"
    fpath_tuned = os.path.join(AUDIO_DIR, fname_tuned)
    async with aiofiles.open(fpath_tuned, "wb") as f:
        await f.write(tuned_bytes)

    # 3. Transcribe with Whisper ASR
    baseline_hypothesis = transcribe_audio(fpath_base, beam_size=EVAL_BEAM_SIZE)
    tuned_hypothesis = transcribe_audio(fpath_tuned, beam_size=EVAL_BEAM_SIZE)

    # 4. Evaluate per-entity EXPECTED vs HEARD matching
    baseline_eval = evaluate_stress_case(raw_text, baseline_hypothesis)
    tuned_eval = evaluate_stress_case(raw_text, tuned_hypothesis)

    return {
        "case_id": case["id"],
        "category": case.get("category", "stress"),
        "difficulty": case.get("difficulty", "hard"),
        "raw_text": raw_text,
        "expected_pronunciation": case.get("expected_pronunciation", tune_for_rime(raw_text)),
        "baseline": {
            "prompt_used": raw_text,
            "audio_url": f"/static/audio/{fname_base}",
            "hypothesis": baseline_hypothesis,
            "evaluation": baseline_eval
        },
        "rimerx": {
            "prompt_used": tuned_prompt,
            "is_safe": tuned_meta["is_safe"],
            "audio_url": f"/static/audio/{fname_tuned}",
            "hypothesis": tuned_hypothesis,
            "evaluation": tuned_eval
        },
        "honest_assessment": {
            "overall_success": tuned_eval["overall_matched"],
            "baseline_accuracy_pct": baseline_eval["accuracy_pct"],
            "rimerx_accuracy_pct": tuned_eval["accuracy_pct"],
            "accuracy_delta_pts": round(tuned_eval["accuracy_pct"] - baseline_eval["accuracy_pct"], 1),
            "limitation_note": tuned_eval["limitation_note"] or baseline_eval["limitation_note"]
        }
    }

# --- METRICS ENDPOINT ---
_epi_instance = None

def get_epitran():
    global _epi_instance
    if _epi_instance is None and Epitran is not None:
        try:
            _epi_instance = Epitran('eng-Latn')
        except Exception as e:
            print(f"[METRICS] Epitran init warning: {e}", flush=True)
            _epi_instance = False
    return _epi_instance if _epi_instance is not False else None

def text_to_phonemes(text):
    words = text.lower().split()
    phonemes = []
    try:
        epi_obj = get_epitran()
    except Exception:
        epi_obj = None

    if epi_obj:
        for w in words:
            try:
                p = epi_obj.transliterate(w)
                phonemes.append(p if p else w)
            except Exception:
                phonemes.append(w)
    else:
        # Fallback to normalized space-separated tokens if Epitran G2P table is unavailable
        phonemes = words

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

    semantic_validation = validate_semantic_preservation(case["raw_text"], prompt_text)

    return {
        "prompt_used": prompt_text,
        "expected_pronunciation": expected_text,
        "pred_phonemes": pred_phonemes,
        "ref_phonemes": ref_phonemes,
        "PER": round(per * 100, 2),
        "CER": round(cer_score * 100, 2),
        "semantic_preservation": semantic_validation,
        "note": "Metric compares Prompt Phonemes vs Gold Phonemes and validates entity preservation."
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

    raw_entities = extract_critical_entities(case["raw_text"])
    entity_verification = verify_critical_entities(raw_entities, hypothesis)

    return {
        "audio_id": filename,
        "audio_file": f"/static/audio/{filename}",
        "reference": reference,
        "hypothesis": hypothesis,
        "words": word_details,
        "WER": wer_score,
        "entity_verification": entity_verification,
        "note": f"ASR Model: {MODEL_SIZE} ({COMPUTE_TYPE}, beam_size={EVAL_BEAM_SIZE})"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
