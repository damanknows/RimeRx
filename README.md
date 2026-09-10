# RimeRx: Indian Pharmacy & Delivery Voice Safety Benchmark

A domain-specific speech synthesis benchmark and prompt-tuning evaluation engine built for **Rime TTS**. RimeRx evaluates and demonstrates how domain-tuned prompt engineering ("writing for the ear") eliminates severe mispronunciations, dosage ambiguities, and address navigation errors in Indian pharmacy prescriptions and logistics instructions.

---

## User Story: Voice Instruction Safety

In fast-paced telehealth, e-pharmacy dispatch, and last-mile delivery across India, text-to-speech (TTS) systems frequently mangle critical medical and location details—turning life-saving instructions like `"Tab Augmentin 625mg 1-0-1 x 5 days"` into incomprehensible digit gibberish (`"one hundred and one"` or `"six hundred twenty five milligrams"`) or garbling dates like `"Exp: 03/26"` into `"zero three slash twenty six"`. RimeRx introduces a deterministic, rule-based prompt normalization layer (`tune_for_rime`) tailored for Rime TTS. By normalizing domain abbreviations, converting dosage schedules into explicit prosodic words (`"one zero one"`), formatting expiration dates (`"Expiry March twenty six"`), splitting digits in high-dosage medications (`"six two five mg"`), and syllabifying Indian proper nouns, RimeRx ensures patient safety and driver accuracy through clear, unambiguous spoken audio.

---

## System Architecture: 9-Step Voice Safety Pipeline

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
   | 1. Text Input             |        | - Rime TTS (mist/v1)      |        | - faster-whisper (small.en) |
   | 2. Critical Entity Extr.  |        | - OpenAI TTS (tts-1)      |        | - EVAL_BEAM_SIZE = 5        |
   | 3. Semantic Preservation  |        | - ElevenLabs (flash v2.5) |        | - jiwer (Word Error Rate)   |
   | 4. Speech Normalization   |        +-------------+-------------+        | - Critical Entity Recall    |
   | 5. Rime TTS (mist/v1)     |                      |                      +-------------+-------------+
   | 6. Audio Generation       |                      |                                    |
   | 7. ASR Transcription      |                      v                                    v
   | 8. Entity Verification    |        +-------------+-------------+        +-------------+-------------+
   | 9. Multi-Metric Scoring   |        |   Reliability & Metrics   |        |   SQLite Ratings Database   |
   +---------------------------+        | (TTFB, Warm/Cold, Status) |        |    (results/benchmark.db)   |
                                        +---------------------------+ <----- +-----------------------------+
```

---

## Rime TTS Configuration

RimeRx utilizes provider-recommended configurations optimized for fast, natural English speech tuned for Indian English accents (`en-IN`).

| Configuration Field | Exact Setting / Value | Notes |
| :--- | :--- | :--- |
| **Model ID** | `mist/v1` | Rime's ultra-low latency production model. |
| **Speaker / Voice ID**| `marsh` | Warm, clear speaker voice tuned for instructions. |
| **Language / Accent** | `en-IN` | English (India) accent support. |
| **Endpoint URL** | `https://users.rime.ai/v1/rime-tts` | Rime HTTP REST TTS API endpoint. |
| **Audio Format** | `mp3` | Compressed audio format for streaming playback. |
| **Transport Protocol** | `HTTP REST (POST)` | Payload: `{"speaker": "marsh", "text": "...", "modelId": "mist/v1", "audioFormat": "mp3"}` |

---

## Setup & Execution Guide

### 1. Prerequisites
- Python 3.10+ (Python 3.13 recommended)
- FFmpeg (for local audio processing)
- NVIDIA GPU with CUDA (Optional; CPU fallback is automatically activated if CUDA is unavailable)

### 2. Installation
Clone the repository and set up a virtual environment:

```bash
# Clone the repository
git clone https://github.com/damanknows/RimeRx.git
cd RimeRx

# Create and activate virtual environment
python -m venv .venv

# On Windows PowerShell:
$env:PYTHONUTF8="1"
.\.venv\Scripts\activate

# On Linux / macOS:
source .venv/bin/activate

# Install core dependencies (<2GB footprint)
pip install -r requirements.txt
```

> **GPU Support Note**: For CUDA GPU acceleration with PyTorch and `faster-whisper`, refer to `requirements-gpu.txt`.

### 3. Environment Configuration
Copy `.env.example` to `.env` and set your API keys:

```bash
cp .env.example .env
```

Configure `.env`:
```env
# Required for primary Rime TTS evaluation
RIME_API_KEY="your_rime_api_key"
RIME_URL="https://users.rime.ai/v1/rime-tts"

# Optional alternative provider keys (for comparative benchmarking & MOS tests)
OPENAI_API_KEY="your_openai_api_key"
ELEVENLABS_API_KEY="your_elevenlabs_api_key"
```

### 4. Running the Web Server
Launch the FastAPI app:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```
Visit **`http://localhost:8000`** to access the interactive web console.

### 5. Running Docker (Optional)
```bash
docker compose up --build
```

### 6. Executing Unit Tests & Benchmark Suite
```bash
# Run pytest unit test suite (66 tests)
pytest tests/ -v

# Run quick benchmark smoke test (3 corpus items)
python run_benchmark.py --limit 3

# Run full corpus benchmark (50 items)
python run_benchmark.py

# Generate executive summary report
python analyze_results.py
```
Outputs will be saved in `results/item_results.csv`, `results/clips/`, and `results/summary.md`.

---

## Benchmark Methodology (5 Pillars)

RimeRx implements a multi-dimensional 5-pillar evaluation methodology:

1. **Word Error Rate (WER)**: Acoustic accuracy metric generated by synthesizing text to audio, transcribing audio back via `faster-whisper` (`small.en`, `int8`, beam size 5), and comparing against normalized ground truth using `jiwer`.
2. **Phoneme Error Rate (PER)**: G2P (Grapheme-to-Phoneme) divergence score calculated using `Epitran` G2P (`hin-Deva` / `eng-Latn`) and normalized Levenshtein edit distance between expected IPA phoneme sequences and prompt text G2P output.
3. **Latency Profiling (TTFB & Total)**: Measures Time-To-First-Byte (`ttfb_ms`) streaming latency and overall request time (`total_ms`). Tracks process-level **Cold** vs. **Warm** runs per provider.
4. **Reliability Rate**: Live in-memory counter (`GET /api/reliability`) tracking total API attempts, 2xx successes, and failure status codes per provider.
5. **Double-Blind MOS (Mean Opinion Score)**: Human listening test framework (`POST /api/blind/session`, `POST /api/mos`). Audio clips from two randomized providers are presented anonymously as "Option A" and "Option B". Ratings (1–5 scale for Naturalness and Intelligibility) are stored in SQLite (`results/benchmark.db`), revealing provider identities only after rating submission.

---

## Known Limitations

- **ASR Ceiling Effect**: Commercial ASR engines (including Whisper `small.en`) occasionally misrecognize complex Indian brand names (*Pantocid*, *Augmentin*, *Dolo*) or localized area names (*BTM 2nd Stage*, *Koramangala*) even when synthesized audio is phonetically clear.
- **Exploratory Corpus Sample Size**: The current evaluation corpus comprises 50 curated items (25 pharmacy items, 25 logistics addresses). While highly effective for identifying severe pronunciation failures, broader production statistical variance requires ongoing corpus expansion.
- **2,500 Character Input Rejection Boundary**: Inputs exceeding 2,500 characters are intentionally rejected with an `HTTP 400 Bad Request` (`Text exceeds maximum length of 2500 characters`). This strict boundary prevents multi-chunk audio concatenation artifacts during latency and WER benchmarking.

---

## Failure Behavior & Resiliency

- **Rate Limit Resilience (HTTP 429)**: The multi-provider TTS engine monitors provider rate limits and transient network timeouts, recording failures in the reliability registry.
- **Missing API Keys**: If an optional provider key (`OPENAI_API_KEY` or `ELEVENLABS_API_KEY`) is missing when selected, the server returns an explicit `HTTP 400 Bad Request` or `HTTP 503 Service Unavailable` response with an actionable error message detailing the missing key rather than unhandled server crashes. If `RIME_API_KEY` is missing on startup, the application raises a clear `RuntimeError` requiring configuration.
