try:
    import torch
    HAS_TORCH = True
except ImportError:
    torch = None
    HAS_TORCH = False

from faster_whisper import WhisperModel
import ctranslate2
import sys
import numpy as np

import os
# 1. MODEL CHOICE: configurable via ASR_MODEL_SIZE (defaults to base.en for free cloud tier 512MB RAM compatibility, small.en for local/GPU)
MODEL_SIZE = os.getenv("ASR_MODEL_SIZE", "base.en")

# 2. QUANTIZATION: int8 is mandatory for memory efficiency.
COMPUTE_TYPE = "int8"

# 3. BEAM SIZE: 1 (Greedy) for interactive use; 5 for WER benchmark evaluation.
BEAM_SIZE = 1
EVAL_BEAM_SIZE = 1 if MODEL_SIZE.startswith("base") else 5

_asr_model = None

def get_asr_model():
    global _asr_model
    if _asr_model is not None:
        return _asr_model

    cuda_available = False
    if HAS_TORCH and torch is not None:
        cuda_available = torch.cuda.is_available()
    else:
        try:
            cuda_available = ctranslate2.get_cuda_device_count() > 0
        except Exception:
            cuda_available = False

    if cuda_available:
        try:
            print("[ASR] Testing CUDA device...", flush=True)
            m = WhisperModel(MODEL_SIZE, device="cuda", compute_type=COMPUTE_TYPE)
            dummy_features = np.zeros((80, 3000), dtype=np.float32)
            m.encode(dummy_features)
            print("[ASR] CUDA device verified & loaded successfully.", flush=True)
            _asr_model = m
            return _asr_model
        except Exception as e:
            print(f"[ASR] CUDA initialization/test failed ({e}), falling back to CPU...", flush=True)

    print(f"[ASR] Loading {MODEL_SIZE} ({COMPUTE_TYPE}) on CPU...", flush=True)
    _asr_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE)
    print("[ASR] Loaded WhisperModel on CPU.", flush=True)
    return _asr_model

# Lazy alias for backwards compatibility
model = None

def transcribe_audio(filepath: str, beam_size: int = EVAL_BEAM_SIZE) -> str:
    global _asr_model
    asr_inst = get_asr_model()
    try:
        segments, _ = asr_inst.transcribe(
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
            _asr_model = WhisperModel(MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE)
            segments, _ = _asr_model.transcribe(
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
