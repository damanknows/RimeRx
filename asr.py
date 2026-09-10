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
    Phase 4 Critical Token Accuracy Metric Engine:
    Compares expected critical entities with ASR transcript and calculates:
    - critical_token_acc: per-sample accuracy % (matched / total * 100)
    - per_entity_results: detailed match status for drug, strength, dose, duration, date, quantity
    - matched_entities & missed_entities
    """
    transcript_lower = asr_transcript.lower()

    fields_to_check = {
        "drug": raw_entities.get("drug"),
        "strength": raw_entities.get("strength"),
        "dose": raw_entities.get("dose") or raw_entities.get("schedule"),
        "frequency": raw_entities.get("frequency"),
        "duration": raw_entities.get("duration"),
        "date": raw_entities.get("date") or raw_entities.get("expiry"),
        "quantity": raw_entities.get("quantity")
    }

    matched_dict = {}
    total_tokens = 0
    matched_tokens = 0

    from data import check_entity_preservation

    for field, val in fields_to_check.items():
        if val is not None:
            total_tokens += 1
            is_matched = check_entity_preservation(field, val, transcript_lower)
            if is_matched:
                matched_tokens += 1
                matched_dict[field] = {"value": val, "matched": True}
            else:
                matched_dict[field] = {"value": val, "matched": False}

    # Number list check for legacy compatibility
    numbers = raw_entities.get("numbers", [])
    num_matched = []
    num_missed = []
    for num_str in numbers:
        is_m = check_entity_preservation("strength", num_str, transcript_lower)
        if is_m:
            num_matched.append(num_str)
        else:
            num_missed.append(num_str)

    sample_acc = round((matched_tokens / total_tokens) * 100, 1) if total_tokens > 0 else 100.0

    return {
        "critical_token_acc": sample_acc,
        "accuracy_pct": sample_acc,
        "total_entities": total_tokens,
        "matched_count": matched_tokens,
        "matched_entities": [v["value"] for v in matched_dict.values() if v["matched"]],
        "missed_entities": [v["value"] for v in matched_dict.values() if not v["matched"]],
        "per_entity_results": matched_dict,
        "number_recall_pct": round(len(num_matched)/len(numbers)*100, 1) if numbers else 100.0
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
