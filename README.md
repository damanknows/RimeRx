# RimeRx: Prompt Tuning Benchmark

A benchmark and prompt tuning environment for evaluating Rime TTS ("Writing for the Ear") performance on domain-specific Indian Pharmacy and Logistics transcriptions.

## Features
- **Deterministic Rime Prompt Tuning (`tune_for_rime`)**: Rule-based prompt normalization expanding domain-specific abbreviations, splitting numerical digits for prosody/clarity, and inserting syllabified phonetic hints for Indian proper nouns.
- **Phoneme Error Rate (PER) & CER Metrics**: Built-in `Epitran` G2P and `jiwer` pipeline measuring phoneme-level distance against gold standard pronunciations.
- **ASR Word Error Rate (WER)**: GPU-accelerated `faster-whisper` (`base.en` with `int8` quantization) on NVIDIA RTX 2050 for acoustic evaluation of generated audio clips.
- **FastAPI + Interactive UI**: Side-by-side comparative UI for default vs tuned prompts, audio playback, and human MOS rubric logging.

---

## Quick Start

### 1. Prerequisites & Environment Setup
```bash
# Set UTF-8 encoding for Windows environment (if applicable)
$env:PYTHONUTF8=1

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` (or set `RIME_API_KEY`):
```env
RIME_API_KEY="your_rime_api_key_here"
RIME_URL="https://users.rime.ai/v1/rime-tts"
```

### 3. Run Application Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Evaluation Metrics

- **PER (Phoneme Error Rate)**: Phoneme-level Levenshtein distance between expected IPA pronunciation and G2P output of prompt text. Lower PER indicates higher prompt alignment for TTS engines.
- **CER (Character Error Rate)**: Normalized character distance across G2P outputs.
- **WER (Word Error Rate)**: Acoustic transcription error calculated via GPU Whisper ASR (`faster-whisper`) on generated `.mp3` audio clips.

---

## Benchmark Results Example

| Case ID | Domain | Raw Text | Default PER | Tuned PER | Delta |
|---|---|---|---|---|---|
| `rx_001` | Pharmacy | `Tab. Augmentin 625mg 1-0-1 x 5 days...` | 18.2% | **4.1%** | **-14.1%** |
| `addr_001` | Delivery | `Deliver to: 12/3, 2nd Cross, BTM...` | 22.5% | **5.3%** | **-17.2%** |
| `rx_002` | Pharmacy | `Syp. Azithral 200mg/5ml - 5ml BD...` | 15.8% | **3.9%** | **-11.9%** |
