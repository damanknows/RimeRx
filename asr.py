from faster_whisper import WhisperModel
import torch
import sys

# 1. MODEL CHOICE: base.en (Best accuracy/speed tradeoff).
#    If OOM: change to "tiny.en"
MODEL_SIZE = "base.en"

# 2. QUANTIZATION: int8 is mandatory for 4GB.
#    "float16" uses ~2.5GB VRAM (Risky with OS overhead).
#    "int8" uses ~1.2GB VRAM (Safe).
COMPUTE_TYPE = "int8"

# 3. BEAM SIZE: 1 (Greedy) = Fastest. 5 = Better accuracy but 3x slower.
#    For WER benchmarking, 1 is standard.
BEAM_SIZE = 1

if torch.cuda.is_available():
    DEVICE = "cuda"
    print(f"[ASR] CUDA device detected: {torch.cuda.get_device_name(0)}", flush=True)
else:
    DEVICE = "cpu"
    print("[ASR] CUDA not available, using CPU", flush=True)

print(f"[ASR] Loading {MODEL_SIZE} ({COMPUTE_TYPE}) on {DEVICE}...", flush=True)
model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
print("[ASR] Model Loaded Successfully.", flush=True)

def transcribe_audio(filepath: str) -> str:
    # VAD_FILTER=True prevents hallucinations on trailing silence (common in TTS)
    segments, _ = model.transcribe(
        filepath,
        beam_size=BEAM_SIZE,
        language="en",
        vad_filter=True,
        condition_on_previous_text=False # Prevents context carry-over errors between short clips
    )
    return " ".join(s.text for s in segments).strip()

if __name__ == "__main__":
    print("[ASR] Testing ASR module initialization...", flush=True)
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
        print(f"[ASR] Transcribing: {audio_path}", flush=True)
        result = transcribe_audio(audio_path)
        print(f"[ASR] Transcription result: {result}", flush=True)
    else:
        print("[ASR] ASR engine ready.", flush=True)
