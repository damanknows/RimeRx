from faster_whisper import WhisperModel
import torch
import sys
import numpy as np

# 1. MODEL CHOICE: small.en for robust pronunciation quality measurement.
MODEL_SIZE = "small.en"

# 2. QUANTIZATION: int8 is mandatory for memory efficiency.
COMPUTE_TYPE = "int8"

# 3. BEAM SIZE: 1 (Greedy) for interactive use; 5 for WER benchmark evaluation.
BEAM_SIZE = 1
EVAL_BEAM_SIZE = 5

def load_asr_model():
    if torch.cuda.is_available():
        try:
            print(f"[ASR] Testing CUDA device: {torch.cuda.get_device_name(0)}...", flush=True)
            m = WhisperModel(MODEL_SIZE, device="cuda", compute_type=COMPUTE_TYPE)
            # Test dummy encode to verify cublas DLL is present
            dummy_features = np.zeros((80, 3000), dtype=np.float32)
            m.encode(dummy_features)
            print("[ASR] CUDA device verified & loaded successfully.", flush=True)
            return m
        except Exception as e:
            print(f"[ASR] CUDA initialization/test failed ({e}), falling back to CPU...", flush=True)

    print(f"[ASR] Loading {MODEL_SIZE} ({COMPUTE_TYPE}) on CPU...", flush=True)
    m = WhisperModel(MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE)
    print("[ASR] Loaded WhisperModel on CPU.", flush=True)
    return m

model = load_asr_model()

def transcribe_audio(filepath: str, beam_size: int = EVAL_BEAM_SIZE) -> str:
    global model
    try:
        segments, _ = model.transcribe(
            filepath,
            beam_size=beam_size,
            language="en",
            vad_filter=True,
            condition_on_previous_text=False # Prevents context carry-over errors between short clips
        )
        return " ".join(s.text for s in segments).strip()
    except Exception as e:
        if "cublas" in str(e).lower() or "cuda" in str(e).lower():
            print(f"[ASR] CUDA runtime error encountered ({e}), switching to CPU fallback...", flush=True)
            model = WhisperModel(MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE)
            segments, _ = model.transcribe(
                filepath,
                beam_size=beam_size,
                language="en",
                vad_filter=True,
                condition_on_previous_text=False
            )
            return " ".join(s.text for s in segments).strip()
        raise

def verify_critical_entities(raw_entities: dict, asr_transcript: str) -> dict:
    """
    Verifies recall of extracted critical prescription entities in the ASR transcript.
    """
    transcript_lower = asr_transcript.lower()
    
    target_items = []
    if "numbers" in raw_entities:
        target_items.extend(raw_entities["numbers"])
    if "drugs" in raw_entities:
        target_items.extend(raw_entities["drugs"])
    if "schedules" in raw_entities:
        target_items.extend(raw_entities["schedules"])

    target_items = list(set(target_items))
    if not target_items:
        return {
            "accuracy_pct": 100.0,
            "total_entities": 0,
            "matched_entities": [],
            "missed_entities": []
        }

    matched = []
    missed = []

    for item in target_items:
        item_lower = item.lower()
        if item_lower in transcript_lower:
            matched.append(item)
            continue

        if item.isdigit():
            from data import num_to_words, DIGIT_WORDS
            w_form = num_to_words(item).lower()
            d_form = " ".join(DIGIT_WORDS[int(d)] for d in item)
            if w_form in transcript_lower or d_form in transcript_lower:
                matched.append(item)
                continue

        if "-" in item and item.replace("-", "").isdigit():
            from data import DIGIT_WORDS
            digits = item.split("-")
            d_words = " ".join(DIGIT_WORDS[int(d)] for d in digits if d.isdigit())
            if d_words in transcript_lower:
                matched.append(item)
                continue

        missed.append(item)

    accuracy_pct = round((len(matched) / len(target_items)) * 100, 1) if target_items else 100.0

    return {
        "accuracy_pct": accuracy_pct,
        "total_entities": len(target_items),
        "matched_entities": matched,
        "missed_entities": missed
    }

if __name__ == "__main__":
    print("[ASR] Testing ASR module initialization...", flush=True)
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
        print(f"[ASR] Transcribing: {audio_path}", flush=True)
        result = transcribe_audio(audio_path)
        print(f"[ASR] Transcription result: {result}", flush=True)
    else:
        print("[ASR] ASR engine ready.", flush=True)
