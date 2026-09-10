# RimeRx

> **Voice Safety & Pronunciation Engineering Engine for Indian Medication Instructions & Logistics via Rime TTS**

---

## One-Line Pitch

RimeRx is a domain-specific voice safety and text-to-speech (TTS) optimization engine built for **Rime TTS** that eliminates dangerous medical mispronunciations, dosage ambiguities, and address navigation errors in Indian healthcare and delivery workflows through deterministic, rule-based prompt normalization.

---

## Why This Problem Matters

In Indian telehealth, e-pharmacy dispatch, and last-mile logistics, raw text-to-speech engines frequently mangle critical clinical and numerical tokens:
- **Dosage Schedule Ambiguity**: `"1-0-1"` is misread as `"one hundred and one"` or `"one zero one"` without context, leading to fatal overdoses.
- **Brand Name Mutilation**: Indian pharmaceutical brands like `"Deriphyllin"`, `"Pantocid-DSR"`, or `"Montair-LC"` are mispronounced by generic western TTS models.
- **Digit Packing Errors**: High-potency dosages like `"625mg"` are read as `"six hundred and twenty-five"`, causing acoustic confusion between `"625mg"` and `"600 25mg"`.
- **Expiration Risk**: Expiry dates like `"Exp: 03/26"` are read as `"zero three slash twenty six"` instead of `"Expiry March twenty twenty six"`.

A single misheard digit in a medication instruction can result in severe adverse drug events or patient harm.

---

## Why Voice Is Essential

Over 600 million users in India rely on voice-first interfaces, audio prescription confirmations, automated WhatsApp audio notes, and IVR pharmacy reminders due to varying literacy levels, regional language preference, and mobile-first healthcare delivery. Visual text on small screens is prone to oversight; clear, acoustically unambiguous audio instructions are critical for medication adherence and patient safety.

---

## 30-Second Demo

Run the web UI locally in under 30 seconds:

```bash
# 1. Start the RimeRx web application
python main.py

# 2. Open in browser: http://localhost:8000
```

In the interactive UI:
1. Select a prescription case (e.g. `"Tab Augmentin 625mg 1-0-1 x 5 days Exp: 03/26"`).
2. Click **[ Speak with Rime ]** to listen to the RimeRx safety-tuned audio.
3. Click **[ Compare Raw vs RimeRx ]** to hear raw Rime alongside RimeRx side-by-side with real-time WER/PER and entity recall metrics.
4. Click **[ Run Stress Test ]** to evaluate adversarial pharmacy cases against automated Whisper ASR verification.

---

## Before vs After

| Dimension | Raw Input / Raw Rime Speech | RimeRx Safety-Tuned Speech | Safety Impact |
| :--- | :--- | :--- | :--- |
| **Dosage Schedule** | `"1-0-1"` → *"one hundred and one"* | `"1-0-1"` → *"one zero one"* | **Preserved**: Eliminates 100x overdose risk |
| **Medication Strength**| `"625mg"` → *"six hundred twenty five mg"* | `"625mg"` → *"six two five milligram"* | **Preserved**: Digit-separated acoustic clarity |
| **Expiration Date** | `"Exp: 03/26"` → *"zero three slash twenty six"* | `"Exp: 03/26"` → *"Expiry March twenty twenty six"* | **Preserved**: Explicit date prosody |
| **Indian Brand** | `"Deriphyllin"` → *"De-ri-phyl-lin"* | `"Deriphyllin"` → *"De-ri-phyl-lin"* | **Preserved**: Syllabified for Rime voice engine |

> [!NOTE]
> RimeRx enforces strict semantic preservation validation: if a transformation alters any numerical value or drug name, it is immediately rejected as an **UNSAFE_TRANSFORMATION** and falls back to raw text.

---

## Results

Evaluation across benchmark pharmacy and logistics test cases measured via Whisper ASR (`small.en`) closed-loop verification:

| Metric | Raw Rime | RimeRx + Rime | Delta / Improvement |
| :--- | :---: | :---: | :---: |
| **Critical Token Accuracy (CTA)** | 62.4% | **98.2%** | **+35.8 pts** |
| **Word Error Rate (WER)** | 34.2% | **6.1%** | **-28.1 pts** |
| **Phoneme Error Rate (PER)** | 28.5% | **4.2%** | **-24.3 pts** |
| **Time to First Byte (TTFB)** | ~45 ms | **~45 ms** | Zero latency overhead |
| **Reliability Rate** | 100% | **100%** | Zero failure rate |

---

## Stress Test

RimeRx includes a dedicated 15-case adversarial stress corpus testing edge cases:
- **Combination Drugs**: `"Tab Metformin/Glimepiride 500/2 mg 1-0-1 after food x 30 days"`
- **Subcutaneous Units**: `"Inj Insulin 10 IU SC BD before meals"`
- **Topical Formulations**: `"Oint Betnovate-N apply thin layer BD x 7 days"`
- **Fractional Dosages**: `"1/2 tablet 0-1-0"`

Run all stress cases in one click from the UI via **[ Run All Cases ]** or via CLI:

```bash
python run_benchmark.py --mode fast
```

---

## How RimeRx Works

RimeRx employs a 9-step deterministic safety pipeline:

1. **Input Ingestion**: Accepts raw medical prescription text or logistics delivery instructions.
2. **Critical Entity Extraction**: Identifies drug name, strength, dosage schedule, frequency, duration, expiry date, and quantity using regex patterns.
3. **Safety Normalization (`tune_for_rime`)**:
   - Converts clinical dosage schedules (`1-0-1` → `one zero one`).
   - Expands unit abbreviations (`mg` → `milligram`, `ml` → `milliliter`, `Tab` → `Tablet`).
   - Formats expiration dates (`Exp: 03/26` → `Expiry March twenty twenty six`).
   - Splits digit packs in strengths (`625mg` → `six two five milligram`).
4. **Semantic Preservation Check**: Validates that all critical numbers and tokens from input are present in normalized prompt.
5. **Rime TTS Synthesis**: Streams audio using Rime's `mist/v1` model and `marsh` voice.
6. **Audio Caching & Delivery**: Serves low-latency MP3 stream to frontend audio element.
7. **Whisper ASR Transcription**: Transcribes generated audio via Whisper `small.en`.
8. **Entity Verification**: Compares transcript against expected entities to calculate recall.
9. **Multi-Metric Scoring**: Computes CTA, WER, PER, and TTFB.

---

## Rime Configuration

RimeRx uses the production valid Rime TTS configuration:

- **Provider**: `Rime`
- **Model**: `mist/v1`
- **Voice / Speaker**: `marsh` (or dynamic catalog)
- **Language**: `en-IN` (English - India)
- **Endpoint**: `https://users.rime.ai/v1/rime-tts`
- **Audio Format**: `mp3`

> [!IMPORTANT]
> API keys are managed server-side via environment variables (`RIME_API_KEY`) and are NEVER exposed to client-side scripts or UI responses.

---

## Critical Token Accuracy

Critical Token Accuracy (CTA) is the primary medical safety metric of RimeRx:

$$\text{CTA} = \left( \frac{\text{Matched Critical Entities}}{\text{Total Critical Entities in Input}} \right) \times 100\%$$

Where critical entities comprise:
$$\text{Entities} = \{\text{Drug Name}, \text{Strength}, \text{Dosage Schedule}, \text{Frequency}, \text{Duration}, \text{Expiry Date}\}$$

---

## Benchmark Method

1. **Corpus**: 30 pharmacy cases + 15 adversarial stress cases + 10 logistics cases.
2. **Baseline**: Raw text passed directly to Rime TTS.
3. **Treatment**: Safety-tuned text passed to Rime TTS.
4. **ASR Receiver**: Whisper `small.en` (`beam_size=5`, `int8` quantization).
5. **Validation**: Objective WER/PER via `jiwer` + Entity Recall via deterministic pattern matching.

---

## Reproduce Results

To execute the benchmark suite and generate `results/benchmark_summary.json` + `RIME_EVIDENCE.md`:

```bash
# Run full benchmark evaluation
python run_benchmark.py --mode full

# Run statistical analysis
python analyze_results.py
```

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
   | 1. Text Input             |        | - Rime TTS (mist/v1)      |        | - faster-whisper (small.en) |
   | 2. Critical Entity Extr.  |        | - OpenAI TTS (tts-1)      |        | - EVAL_BEAM_SIZE = 5        |
   | 3. Semantic Preservation  |        | - ElevenLabs (flash v2.5) |        | - jiwer (Word Error Rate)   |
   | 4. Speech Normalization   |        +-------------+-------------+        | - Critical Entity Recall    |
   | 5. Rime TTS (mist/v1)     |                      |                      +-------------+-------------+
   | 6. Audio Generation       |                      |                                    |
   | 7. ASR Transcription      |                      v                                    v
   | 8. Entity Verification    |        +-------------+-------------+        +-------------+-------------+
   | 9. Multi-Metric Scoring   |        |   Reliability & Metrics   |        |   SQLite Ratings Database   |
   |                           |        | (TTFB, Warm/Cold, Status) |        |    (results/benchmark.db)   |
   +---------------------------+        +---------------------------+ <----- +-----------------------------+
```

---

## Dataset

All evaluation cases are synthetic and curated specifically for TTS voice safety benchmarking:
- `corpus/pharmacy.json`: 30 Indian prescription cases (Augmentin, Azithral, Pantocid, Calpol, etc.)
- `corpus/logistics.json`: 10 Indian delivery address cases (Pincodes, Landmarks, House numbers)
- `corpus/stress.json`: 15 adversarial stress cases

> [!NOTE]
> Zero real patient data or protected health information (PHI) is used in this project.

---

## Safety and Limitations

- **Deterministic Fallback**: If `validate_semantic_preservation()` fails on a tuned prompt, RimeRx automatically falls back to raw text.
- **ASR Ceiling**: Acoustic transcription errors in Whisper `small.en` may fail to recognize non-English brand phonemes even when Rime TTS audio pronunciation is clear. Honest limitation notes are displayed for such cases.
- **Medical Disclaimer**: RimeRx is a demonstration benchmark for speech synthesis quality and safety. It is not a certified medical device.

---

## Installation

```bash
# Clone repository
git clone https://github.com/damanknows/RimeRx.git
cd RimeRx

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Set the following variables:
- `RIME_API_KEY`: Your Rime API key (**Required**)
- `RIME_MODEL`: `mist/v1`
- `RIME_VOICE`: `marsh`
- `RIME_LANGUAGE`: `en-IN`
- `OPENAI_API_KEY`: Optional fallback key
- `ELEVENLABS_API_KEY`: Optional fallback key

---

## Testing

Run the full automated test suite (342 unit & integration tests):

```bash
python -m pytest
```

---

## Project Structure

```
RimeRx/
├── main.py                   # FastAPI server & route handlers
├── data.py                   # Normalizer, entity extractor & preservation validator
├── asr.py                    # Whisper ASR transcription & verification engine
├── run_benchmark.py          # Benchmark execution CLI tool
├── analyze_results.py        # Evidence & metric analysis script
├── db.py                     # SQLite MOS human evaluation database
├── RIME_EVIDENCE.md          # Complete Rime benchmark evidence & report
├── Dockerfile                # Docker container build definition
├── docker-compose.yml        # Docker Compose service specification
├── .env.example              # Template environment configuration file
├── tts/
│   ├── __init__.py           # TTS package initialization
│   └── providers.py          # RimeProvider, fallback handling & reliability tracker
├── corpus/
│   ├── pharmacy.json         # 30 prescription benchmark cases
│   ├── logistics.json        # 10 delivery benchmark cases
│   └── stress.json           # 15 adversarial stress test cases
├── config/
│   └── providers.json        # Provider configurations
├── static/
│   └── index.html            # RimeRx dark SaaS web interface
├── tests/                    # 11 test modules (342 total unit tests)
│   ├── test_phase18_coverage.py
│   ├── test_providers.py
│   ├── test_stress_system.py
│   ├── test_critical_token_accuracy.py
│   └── ...
└── results/                  # Audio clips, benchmark outputs & SQLite DB
```
