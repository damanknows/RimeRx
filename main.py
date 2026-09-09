import os, httpx, asyncio, uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from data import TEST_CASES, tune_for_rime
from dotenv import load_dotenv
import uvicorn

load_dotenv()
RIME_API_KEY = os.getenv("RIME_API_KEY", "LGalOxBRAhzEctoceMBFmC92gSmppxEM-9WsB9ohqS0")
RIME_URL = os.getenv("RIME_URL", "https://users.rime.ai/v1/rime-tts")
HEADERS = {
    "Authorization": f"Bearer {RIME_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "audio/mp3"
}

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
AUDIO_DIR = "static/audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

class RenderRequest(BaseModel):
    case_id: str
    prompt_type: str # "default" | "tuned"

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("static/index.html") as f: return f.read()

@app.get("/api/cases")
async def get_cases():
    return [{"id": c["id"], "domain": c["domain"], "text": c["raw_text"]} for c in TEST_CASES]

@app.post("/api/render")
async def render_audio(req: RenderRequest):
    case = next((c for c in TEST_CASES if c["id"] == req.case_id), None)
    if not case: raise HTTPException(404, "Case not found")

    text = case["raw_text"] if req.prompt_type == "default" else tune_for_rime(case["raw_text"])

    # Chunk text if > 2500 characters
    if len(text) > 2500:
        text = text[:2500]

    # Rime Payload using verified speaker 'marsh' and audioFormat 'mp3'
    payload = {
        "speaker": "marsh",
        "text": text,
        "audioFormat": "mp3"
    }

    fname = f"{req.case_id}_{req.prompt_type}_{uuid.uuid4().hex[:4]}.mp3"
    fpath = os.path.join(AUDIO_DIR, fname)

    # Retry logic (1 retry for 429/timeout/5xx)
    last_error = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(RIME_URL, json=payload, headers=HEADERS)
                if resp.status_code == 200:
                    with open(fpath, "wb") as f:
                        f.write(resp.content)
                    return {"audio_url": f"/static/audio/{fname}", "prompt_used": text}
                elif resp.status_code == 429 or resp.status_code >= 500:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:150]}"
                    await asyncio.sleep(1.0) # wait before retry
                    continue
                else:
                    raise HTTPException(resp.status_code, f"Rime API Error: {resp.text[:200]}")
        except httpx.TimeoutException as e:
            last_error = f"Timeout: {e}"
            await asyncio.sleep(1.0)
        except HTTPException:
            raise
        except Exception as e:
            last_error = str(e)
            await asyncio.sleep(1.0)

    raise HTTPException(500, f"Rime API Failed after retries: {last_error}")

# --- METRICS ENDPOINT ---
from epitran import Epitran
from jiwer import wer, cer
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

@app.post("/api/evaluate")
async def evaluate(req: RenderRequest):
    case = next((c for c in TEST_CASES if c["id"] == req.case_id), None)
    if not case: raise HTTPException(404, "Case not found")

    # We compare Generated Phonemes vs Expected Phonemes
    # Note: This requires the *generated audio* to be transcribed (ASR) for true WER.
    # SPEED HACK (4 hrs): We compare the *Prompt Text Phonemes* vs *Expected Phonemes*.
    # This measures "Prompt Engineering Quality", not "TTS Acoustic Quality".
    # Label it clearly in UI: "Prompt-Phoneme Distance (Lower=Better)"

    prompt_text = case["raw_text"] if req.prompt_type == "default" else tune_for_rime(case["raw_text"])
    expected_text = case["expected_pronunciation"]

    pred_phonemes = text_to_phonemes(prompt_text)
    ref_phonemes = text_to_phonemes(expected_text)

    per = wer(ref_phonemes, pred_phonemes) # Phoneme Error Rate
    cer_score = cer(ref_phonemes, pred_phonemes)

    return {
        "prompt_used": prompt_text,
        "expected_pronunciation": expected_text,
        "pred_phonemes": pred_phonemes,
        "ref_phonemes": ref_phonemes,
        "PER": round(per * 100, 2),
        "CER": round(cer_score * 100, 2),
        "note": "Metric compares Prompt Phonemes vs Gold Phonemes. True WER requires ASR on audio."
    }

from asr import transcribe_audio, MODEL_SIZE
from jiwer import wer

@app.post("/api/wer")
async def calculate_true_wer(req: RenderRequest):
    case = next((c for c in TEST_CASES if c["id"] == req.case_id), None)
    if not case: raise HTTPException(404, "Case not found")

    # 1. Find the LATEST generated audio file for this case/type
    import glob
    pattern = os.path.join(AUDIO_DIR, f"{req.case_id}_{req.prompt_type}_*.mp3")
    files = glob.glob(pattern)
    if not files:
        raise HTTPException(400, "Audio not generated yet. Click 'Generate' first.")
    latest_audio = max(files, key=os.path.getctime)

    # 2. TRANSCRIBE (Blocking! ~2-5s per clip on 2050)
    # Run in threadpool to not block event loop
    loop = asyncio.get_event_loop()
    hypothesis = await loop.run_in_executor(None, transcribe_audio, latest_audio)

    # 3. Normalize & Calculate WER
    from jiwer import ProcessWords, RemovePunctuation, LowerCase, Strip
    transform = ProcessWords([LowerCase(), RemovePunctuation(), Strip()])

    reference = case["expected_pronunciation"] # Your gold text

    wer_score = wer(reference, hypothesis, truth_transform=transform, hypothesis_transform=transform)

    return {
        "audio_file": latest_audio,
        "reference": reference,
        "hypothesis": hypothesis,
        "WER": round(wer_score * 100, 2),
        "note": f"ASR Model: {MODEL_SIZE} (faster-whisper int8)"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
