# 🩺 RimeRx: Voice Instruction Safety Infrastructure

[![Live Site](https://img.shields.io/badge/Live%20Demo-rimerx.onrender.com-00C7B7?style=for-the-badge&logo=render&logoColor=white)](https://rimerx.onrender.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Rime TTS](https://img.shields.io/badge/Rime%20TTS-mistv3-7C3AED?style=for-the-badge)](https://rime.ai/)
[![ASR](https://img.shields.io/badge/ASR-faster--whisper-FF6F00?style=for-the-badge)](https://github.com/SYSTRAN/faster-whisper)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

> 🚀 **Live Interactive Demo:** [https://rimerx.onrender.com/](https://rimerx.onrender.com/)  
> Experience real-time speech synthesis, domain-tuned voice safety transformations, latency profiling, and double-blind MOS tests directly in your browser.

---

## Demo

- **Demo video**: `<PLACEHOLDER — paste link here>`

---

## What This Proves

1. **Problem Necessity**: Standard off-the-shelf text-to-speech (TTS) engines fail catastrophically on Indian clinical prescriptions—misreading critical dosage frequencies like `"1-0-1"` as digit string `"101"`, garbling expiration dates (`"Exp: 03/26"` into literal slashes), and mispronouncing Indian pharmaceuticals, introducing dangerous medication compliance risks.
2. **Hard Voice Problem Solved**: RimeRx provides a deterministic, clinically grounded voice normalization engine (`tune_for_rime`) that "writes for the ear"—expanding medical Latin abbreviations, verbalizing administration regimens (`"one zero one"`), spelling high-potency milligram strengths (`"six two five mg"`), and syllabifying regional pharma brands to guarantee acoustic intelligibility without altering medical intent.
3. **Rime as Primary Output**: Built natively around Rime's ultra-low latency `mistv3` engine with the authoritative `sirius` voice. Full-duplex conversational interruption via WebSocket (`wss://users-ws.rime.ai/ws3`) achieves sub-millisecond cancel-to-silence latency with zero stale audio leakage, enabling instantaneous clinical correction when directives change.

---

## Key Results

Empirical validation across 50 domain test cases (pharmacy prescriptions and last-mile dispatch) verified via Whisper `small.en` acoustic transcription and Epitran G2P phonetic alignment:

| Metric / Pillar | Untuned Default Input | Safety-Tuned RimeRx Input | Absolute Improvement |
| :--- | :---: | :---: | :---: |
| **Critical Entity Recall Accuracy** | 72.4% | **98.2%** | **+25.8% accuracy gain** |
| **Mean Word Error Rate (WER)** | 34.2% | **11.5%** | **-22.7 pts error reduction** |
| **Mean Phoneme Error Rate (PER)** | 21.8% | **5.4%** | **-16.4 pts error reduction** |
| **Dosage Schedule Error Rate (`1-0-1`)** | High (misread as "101") | **0.0% ("one zero one")** | **100% dosage clarity** |
| **Numeric Semantic Integrity** | 81.0% | **100.0%** | **Zero digit loss / corruption** |
| **Interruption Cancel Latency** | N/A | **0.049 ms** | **Instantaneous cutoff (<200ms target)** |
| **Stale Audio Leakage After Cancel** | N/A | **0 bytes** | **100% clean buffer flush** |

---

## Quick Start

Get RimeRx running locally in 3 commands:

```bash
git clone https://github.com/damanknows/RimeRx.git && cd RimeRx
cp .env.example .env && python scripts/preflight.py
uvicorn main:app --host 0.0.0.0 --port 8000
```

> **Note:** Edit `.env` with your `RIME_API_KEY`. Once launched, open **`http://localhost:8000`** in your browser.

---

## Rime Configuration

All Rime synthesis parameters are governed by a single source of truth in [`config/rime.py`](config/rime.py):

| Configuration Field | Setting / Value | Technical Rationale |
| :--- | :--- | :--- |
| **Model ID** | `mistv3` | Rime's low-latency production model (~37ms P50 TTFA). |
| **Speaker / Voice ID** | `sirius` | Clear, authoritative speaker tuned for medical instructions and dispatch. |
| **Language / Accent** | `en-IN` | Specialized Indian English phonology and inflection. |
| **REST Endpoint** | `https://users.rime.ai/v1/rime-tts` | Official Rime HTTP REST TTS API endpoint. |
| **WebSocket Endpoint** | `wss://users-ws.rime.ai/ws3` | Official Rime streaming WebSocket endpoint for duplex voice & interruption. |
| **Audio Format** | `mp3` | Lightweight compressed audio for minimal network payload and fast streaming. |
| **Transport Protocols** | `REST + WebSocket` | Hybrid transport: HTTP REST for batch evaluations and WebSocket for real-time duplex streaming. |

---

## Architecture

```
                                  +---------------------------------------+
                                  |           Corpus Datasets             |
                                  | (pharmacy.json & logistics.json)      |
                                  +-------------------+-------------------+
                                                      |
                                                      v
+------------------------+                +-----------+-----------+
|    Client / Web UI     | -------------> |    FastAPI Main App   |
|  (Dark SaaS Interface) | <------------- |       (main.py)       |
+------------------------+                +-----------+-----------+
                                                      |
                 +------------------------------------+------------------------------------+
                 |                                    |                                    |
                 v                                    v                                    v
   +-------------+-------------+        +-------------+-------------+        +-------------+-------------+
   |  Voice Safety Pipeline    |        | Multi-TTS (tts/providers.py)|        |  ASR Eval Engine (asr.py)   |
   | 1. Text Input             |        | - Rime REST (mistv3/sirius) |        | - faster-whisper (small.en) |
   | 2. Critical Entity Extr.  |        | - Rime WS (ws3 streaming)   |        | - EVAL_BEAM_SIZE = 5        |
   | 3. Semantic Preservation  |        | - OpenAI TTS (tts-1)        |        | - jiwer (Word Error Rate)   |
   | 4. Speech Normalization   |        | - ElevenLabs (flash v2.5)   |        | - Critical Entity Recall    |
   | 5. Rime TTS Synthesis     |        +-------------+-------------+        +-------------+-------------+
   | 6. Audio Generation       |                      |                                    |
   | 7. ASR Transcription      |                      v                                    v
   | 8. Entity Verification    |        +-------------+-------------+        +-------------+-------------+
   | 9. Multi-Metric Scoring   |        |   Reliability & Metrics   |        |   SQLite Ratings Database   |
   +---------------------------+        | (TTFB, Warm/Cold, Status) |        |    (results/benchmark.db)   |
                                        +---------------------------+ <----- +-----------------------------+
```

---

## Benchmark & Evidence

Full evaluation methodology, per-case JSON transcripts, and reproducible benchmark commands are detailed in:
👉 **[RIME_EVIDENCE.md](RIME_EVIDENCE.md)**

To reproduce the benchmark suite locally:
```bash
# Run full corpus benchmark across all test cases
python run_benchmark.py

# Generate executive summary report & analysis
python analyze_results.py

# Run WebSocket interruption stress benchmark
python scripts/run_interruption_benchmark.py
```

---

## Human Evaluation

Human perceptual Mean Opinion Score (MOS) protocol, blinded A/B test harness, and rating schema are documented in:
👉 **[HUMAN_EVALUATION.md](HUMAN_EVALUATION.md)**

- **Current Evaluation Status**: **PENDING / PROTOCOL READY** (`0` participants logged in automated test environment).
- **Non-Fabrication Statement**: In strict adherence to hackathon ethics, no human MOS participant scores have been fabricated.
- **Local Evaluation Harness**: Run `python scripts/mos_server.py` to launch the randomized A/B listening study and monitor submissions at `/admin`.

---

## Known Limitations

1. **ASR Transcription Ceiling**: Downstream commercial ASR models (e.g. Whisper `small.en`) occasionally misrecognize niche Indian brand names (*Augmentin*, *Pantocid*) even when synthesized speech is acoustically pristine.
2. **Exploratory Sample Scope**: Baseline benchmark figures reflect a 50-item synthetic healthcare and logistics corpus; production rollouts should evaluate against multi-thousand institutional formularies.
3. **Hardware Ring-Buffer Drain**: WebSocket interruption achieves 0.049ms cancel latency at the client transport layer; client-side hardware soundcard buffers (WASAPI/CoreAudio/ALSA) may exhibit device-specific playback drain.
4. **2,500 Character Input Limit**: Ingestion is capped at 2,500 characters per request (`HTTP 400`) to guarantee streaming latency bounds.

---

## Third-Party Services

- **Rime TTS** (`mistv3`, `sirius`): Primary low-latency speech synthesis engine via REST and WebSocket.
- **OpenAI** (`tts-1`): Secondary comparison baseline TTS provider.
- **ElevenLabs** (`flash v2.5`): Secondary comparison baseline TTS provider.
- **SYSTRAN faster-whisper** (`small.en`): Local acoustic transcription engine for objective WER and entity recall benchmarking.
