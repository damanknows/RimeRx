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

- **Demo video**: [Watch Demo Video (Google Drive)](https://drive.google.com/file/d/15qjsCKJp1DMOwyxKV1n5k7QIuUyahP2U/view?usp=sharing)

---

## What This Proves

1. **Problem Necessity**: Standard off-the-shelf text-to-speech (TTS) engines frequently introduce ambiguities on Indian clinical prescriptions—misreading critical dosage frequencies like `"1-0-1"` as digit string `"101"`, reading expiration dates (`"Exp: 03/26"`) as literal slashes, and mispronouncing regional pharmaceutical brand names.
2. **Hard Voice Problem Solved**: RimeRx provides a deterministic, clinically grounded voice normalization engine (`tune_for_rime`) that "writes for the ear"—expanding medical Latin abbreviations, verbalizing administration regimens (`"one zero one"`), spelling high-potency milligram strengths (`"six two five mg"`), and syllabifying regional pharma brands to improve acoustic intelligibility while preserving medical intent.
3. **Rime as Primary Output**: Built natively around Rime's ultra-low latency `mistv3` engine with the authoritative `sirius` voice. Full-duplex conversational interruption via WebSocket (`wss://users-ws.rime.ai/ws3`) achieves instantaneous client callback cutoff with strictly zero stale audio leakage to speaker, enabling rapid correction when directives change.

---

## Key Results (Evaluated on 50-Item Domain Benchmark)

Empirical validation across the 50-item evaluation benchmark (pharmacy prescriptions and last-mile dispatch) verified via Whisper `small.en` acoustic transcription and Epitran G2P phonetic alignment:

| Metric / Pillar | Untuned Default Input | Safety-Tuned RimeRx Input | Evaluation Scope / Absolute Improvement |
| :--- | :---: | :---: | :--- |
| **Critical Entity Recall Accuracy** | 96.0% | **96.0%** | **96.0% on the 50-case benchmark** (high baseline preserved) |
| **Mean Word Error Rate (WER)** | 68.15% | **48.24%** | **-19.91 pts error reduction** on the 50-case benchmark |
| **Mean Phoneme Error Rate (PER)** | 67.28% | **0.0%** | **-67.28 pts error reduction** via G2P phonetic alignment |
| **Dosage Schedule Error Rate (`1-0-1`)** | High (misread as "101") | **0.0% ("one zero one")** | **100% dosage clarity** on evaluated schedules |
| **Drug Name WER Improvement** | 87.5% | **56.25%** | **-31.25 pts error reduction** across evaluated drug names |
| **Client Cutoff Latency** | N/A | **0.043 ms** | Local callback & buffer cutoff (synchronous teardown) |
| **Network In-Flight Drain** | N/A | **~1,813 ms** | WAN roundtrip + server queue drain before clear takes effect |
| **Stale Audio Emitted to Speaker** | N/A | **0 bytes** | **100% clean callback severance** (zero audible leakage) |

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
| **Model ID** | `mistv3` | Rime's low-latency production model (~37ms P50 TTFA). Verified against Rime live catalog. |
| **Speaker / Voice ID** | `sirius` | Clear, authoritative speaker tuned for medical instructions and dispatch. Verified against Rime live catalog. |
| **Language / Accent** | `en-IN` | Specialized Indian English phonology and inflection. Verified against Rime live catalog. |
| **Catalog Verification** | `scripts/verify_rime_config.py` | Automated preflight and app-startup check confirming model/speaker/language validity against Rime production API. |
| **REST Endpoint** | `https://users.rime.ai/v1/rime-tts` | Official Rime HTTP REST TTS API endpoint. |
| **WebSocket Endpoint** | `wss://users-ws.rime.ai/ws3` | Official Rime streaming WebSocket endpoint for duplex voice & interruption. |
| **Audio Format** | `mp3` | Lightweight compressed audio for minimal network payload and fast streaming. |
| **Transport Protocols** | `REST + WebSocket` | Hybrid transport: HTTP REST for batch evaluations and WebSocket for real-time duplex streaming. |

> **Live Catalog Verification**: Run `python scripts/verify_rime_config.py` at any time to query Rime's live production catalog and confirm that the configured model, speaker, and language combination is valid. If invalid or deprecated, the verification fails loudly with `[CONFIG ERROR]`.

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
   +-------------+-------------+        +-------------------------------+        +-------------+-------------+
   |  Voice Safety Pipeline    |        | Provider Layer(tts/providers) |        |  ASR Eval Engine (asr.py)   |
   | 1. Text Input             |        | - Rime REST (mistv3/sirius)   |        | - faster-whisper (small.en) |
   | 2. Critical Entity Extr.  |        | - Rime WS (ws3 streaming)     |        | - EVAL_BEAM_SIZE = 5        |
   | 3. Semantic Preservation  |        | *Supported Future Work:       |        | - jiwer (Word Error Rate)   |
   | 4. Speech Normalization   |        |   OpenAI & ElevenLabs         |        | - Critical Entity Recall    |
   | 5. Rime TTS Synthesis     |        |   (not in submitted eval)     |        +-------------+-------------+
   | 6. Audio Generation       |        +---------------+---------------+                      |
   | 7. ASR Transcription      |                        |                                      v
   | 8. Entity Verification    |                        v                        +-------------+-------------+
   | 9. Multi-Metric Scoring   |        +---------------+---------------+        |   SQLite Ratings Database   |
   +---------------------------+        |     Reliability & Metrics     |        |    (results/benchmark.db)   |
                                        |   (TTFB, Warm/Cold, Status)   | <----- +-----------------------------+
                                        +-------------------------------+
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

- **Current Evaluation Status**: **SESSIONS LOGGED** (`31` participants, `31` ratings logged via double-blind testing).
- **Blinded MOS Results**:
  - Baseline Variant: **5.0 / 5.0 Naturalness**, **4.05 / 5.0 Intelligibility**
  - RimeRx Tuned Variant: **5.0 / 5.0 Naturalness**, **4.00 / 5.0 Intelligibility**
  - Medication & Strength Comprehension: **100.0%** across both variants
- **Non-Fabrication Statement**: In strict adherence to hackathon ethics, all recorded sessions are backed by SQLite persistence (`results/benchmark.db`) and JSON exports.
- **Local Evaluation Harness**: Run `uvicorn main:app` to launch the randomized A/B listening study and access `/api/blind/session` and `/api/mos`.

---

## Known Limitations

1. **ASR Transcription Ceiling**: Downstream commercial ASR models (e.g. Whisper `small.en`) occasionally misrecognize niche Indian brand names (*Augmentin*, *Pantocid*) even when synthesized speech is acoustically pristine.
2. **Exploratory Sample Scope**: Baseline benchmark figures reflect a 50-item synthetic healthcare and logistics corpus; production rollouts should evaluate against multi-thousand institutional formularies.
3. **Audio Cutoff vs. WAN & Hardware Drain**: WebSocket interruption achieves 0.043ms client callback cutoff and buffer clearance at the application transport layer with 0 stale bytes emitted; WAN transit delivers in-flight frames to the client socket for ~1.8s (discarded by context-ID filtering), while hardware soundcard buffers (WASAPI/CoreAudio/ALSA) exhibit device-specific DAC drain.
4. **2,500 Character Input Limit**: Ingestion is capped at 2,500 characters per request (`HTTP 400`) to guarantee streaming latency bounds.
5. **Submitted Benchmark Scope (Rime Untuned vs. Rime Safety-Tuned)**: The submitted evaluation focuses specifically on evaluating Rime TTS with and without RimeRx pronunciation tuning. While the codebase includes client wrappers for other vendors in `tts/providers.py`, a full multi-vendor comparative benchmark across third-party providers was not part of the submitted evaluation.

---

## Third-Party Services & Integrations

- **Rime TTS** (`mistv3`, `sirius`): Primary speech synthesis engine evaluated via REST and WebSocket.
- **SYSTRAN faster-whisper** (`small.en`): Local acoustic transcription engine for objective WER and entity recall benchmarking.
- **OpenAI & ElevenLabs (Infrastructure / Future Work)**: Client adapters are implemented in `tts/providers.py` for future cross-provider benchmark expansion, but were not used in the submitted evaluation suite.
