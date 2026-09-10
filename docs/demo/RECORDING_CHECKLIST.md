# 📹 RimeRx Demo Video Recording Checklist

Ensure each of the following elements is explicitly visible on screen during video capture to satisfy judge review and rubric criteria:

---

### Mandatory On-Screen Indicators

- [ ] **Repository URL / Codebase Origin**:
  - Browser tab or editor showing `https://github.com/damanknows/RimeRx` or local path `d:\data forge\rimerx`.
- [ ] **Active TTS Provider Indicator**:
  - Green status pill in Web UI header: `Active Provider: Rime (mistv3 / sirius)`.
  - Console / terminal log displaying live dispatch:
    `Dispatching to Rime TTS API: https://users.rime.ai/v1/rime-tts`.
- [ ] **Rime Model ID**:
  - Visible on UI badge and in `config/rime.py` / `.env`: `mistv3`.
- [ ] **Rime Speaker ID**:
  - Visible on UI badge and in `config/rime.py` / `.env`: `sirius`.
- [ ] **Rime Endpoint**:
  - REST: `https://users.rime.ai/v1/rime-tts`
  - WebSocket: `wss://users-ws.rime.ai/ws3`
- [ ] **Language / Accent**:
  - Visible in configuration: `en-IN` (Indian English).
- [ ] **Audio Format**:
  - Visible in configuration and network inspection: `mp3`.
- [ ] **Side-by-Side Audio Comparison**:
  - Visual wave/playback controls for **Option A (Raw Baseline)** vs **Option B (RimeRx Safety-Tuned)**.
- [ ] **Live Acoustic ASR Evaluation**:
  - Whisper `small.en` live transcription showing Word Error Rate (WER) and Phoneme Error Rate (PER) improvement.
- [ ] **Terminal Benchmark & Interruption Proof**:
  - Terminal showing execution of `python run_benchmark.py` and `python scripts/run_interruption_benchmark.py` with 0.049ms cancel latency and 0 stale bytes.
- [ ] **Transparent Status of Human Evaluation**:
  - `HUMAN_EVALUATION.md` visible with `PENDING / 0 participants` and the Non-Fabrication Statement intact.
