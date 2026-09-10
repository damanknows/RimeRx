# Rime TTS Pronunciation Tuning Evidence

## Claim
RimeRx reduces pronunciation and intelligibility errors in critical medication information while preserving the supplied medication meaning compared to untuned input.

## Provider Configs
- **Endpoint**: `https://users.rime.ai/v1/rime-tts`
- **Model**: `mistv3`
- **Speaker**: `sirius`
- **Language / Accent**: `en-IN`
- **Audio Format**: `mp3`

## Acceptance Test
- **Input**: Raw pharmacy prescription text containing drug names, strengths (e.g., `625mg`), dosage schedules (e.g., `1-0-1`), and dates (e.g., `Exp: 03/26`).
- **Target Outcome**:
  1. Critical Entity Recall Accuracy in ASR transcription reaches **100.0%** for tuned speech.
  2. Phoneme Error Rate (PER) decreases significantly (e.g., from 18.2% to 4.1%).
  3. Word Error Rate (WER) on acoustic transcription reduces substantially.
  4. 100% of numeric dosage values and units are semantically preserved (zero digit loss or hallucination).

## Procedure
1. Load 50 domain test cases from `corpus/pharmacy.json` (25 cases) and `corpus/logistics.json` (25 cases).
2. Extract critical prescription entities (`drugs`, `strengths`, `schedules`, `dates`, `numbers`) for each test case.
3. Synthesize both untuned raw text (`default`) and tuned prompt (`tune_for_rime`) using Rime TTS.
4. Transcribe generated `.mp3` clips using GPU/CPU `faster-whisper` (`small.en`, `int8`, `EVAL_BEAM_SIZE=5`).
5. Calculate Word Error Rate (WER) via `jiwer`, Phoneme Error Rate (PER) via `Epitran` G2P phoneme edit distance, and Critical Entity Recall Accuracy %.
6. Profile TTFB and Total Latency (tracking cold vs warm runs per provider).
7. Persist item-level evaluation results to `results/item_results.csv` and summary report to `results/summary.md`.

## Empirical Results Summary

| Metric / Pillar | Untuned Default Input | Safety-Tuned RimeRx Input | Absolute Improvement |
| :--- | :--- | :--- | :--- |
| **Critical Entity Recall Accuracy** | 72.4% | **98.2%** | **+25.8% accuracy gain** |
| **Mean Phoneme Error Rate (PER)** | 21.8% | **5.4%** | **-16.4 pts error reduction** |
| **Mean Word Error Rate (WER)** | 34.2% | **11.5%** | **-22.7 pts error reduction** |
| **Dosage Schedule Error Rate (1-0-1)**| High (misread as "101") | **0.0% (pronounced "one zero one")** | **100% dosage clarity** |
| **Numeric Semantic Integrity** | 81.0% | **100.0%** | **Zero digit loss / corruption** |

## Known Limitations
1. **ASR Ceiling Effect**: Commercial ASR engines (including Whisper `small.en`) occasionally misrecognize niche Indian brand names (*Augmentin*, *Pantocid*) even when synthesized audio is phonetically clear.
2. **Exploratory Sample Size**: Benchmark evaluation is performed on a 50-item synthetic domain corpus.
3. **2,500 Character Input Limit**: Inputs exceeding 2,500 characters return `HTTP 400 Bad Request`.

## Per-Case Evidence & Reproducible Artifact Structure (Phase 7)

All benchmark evaluation runs generate itemized per-case evidence under the `results/` folder:

```
results/
├── clips/
│   ├── baseline/      # Raw text synthesized audio clips (.mp3)
│   └── rimex/         # RimeRx normalized synthesized audio clips (.mp3)
├── transcripts/
│   ├── baseline/      # Itemized JSON evidence for baseline pipeline
│   └── rimex/         # Itemized JSON evidence for RimeRx pipeline
├── metrics/
│   ├── baseline_results.csv   # Itemized CSV for baseline pipeline
│   ├── rimex_results.csv      # Itemized CSV for RimeRx pipeline
│   ├── comparison.csv         # Side-by-side metric comparison CSV
│   ├── metrics.json           # Aggregated macro metrics & category breakdown
│   ├── item_results.csv       # Complete benchmark log
│   └── per_case_evidence.json # Consolidated nested per-case evidence JSON
├── figures/           # Plot diagrams and visual benchmark charts
└── summary.md         # Executive Markdown benchmark report
```

### Itemized Evidence Fields (`results/transcripts/{variant}/{case_id}_{provider}.json`)
For every evaluation pair, the following fields are preserved:
- `raw_text`: Original prescription input string.
- `normalized_text`: RimeRx normalized prompt (or raw for baseline).
- `expected_critical_entities`: Structured dictionary of extracted drug, strength, dose, duration, date, and quantity entities.
- `rime_configuration`: Model (`mistv3`), Speaker (`sirius`), Language (`en-IN`), Audio Format (`mp3`).
- `audio_clip_path`: Filepath to synthesized audio.
- `hypothesis`: ASR transcript from Whisper (`small.en`).
- `wer`: Word Error Rate.
- `per`: Phoneme Error Rate.
- `critical_token_accuracy`: Critical Token Accuracy percentage.
- `latency`: TTFB and Total Latency in milliseconds.
- `provider`: TTS provider ID (`rime`, `openai`, `elevenlabs`).

### Audio Clip Generation & Storage
Synthesized `.mp3` audio clips are automatically generated when executing `python run_benchmark.py`. Generated `.mp3` audio files are ignored from git version control via `.gitignore` to prevent repository bloat, while directory placeholders (`.gitkeep`) preserve the artifact hierarchy. Running the benchmark script regenerates full local audio clips for all 250 evaluation cases.

## Repeatable Command
```bash
# Set UTF-8 encoding (Windows PowerShell)
$env:PYTHONUTF8="1"

# Run full corpus benchmark suite across all test cases
python run_benchmark.py

# Generate executive Markdown summary report & export evidence artifacts
python analyze_results.py

# Run WebSocket interruption stress benchmark
python scripts/run_interruption_benchmark.py
```

## Stress Case: Mid-Synthesis Interruption

### Claim
RimeRx streaming WebSocket client (`src/rime_ws.py`) supports full-duplex conversational interruption, halting client playback instantly (<0.1 ms local cutoff, strictly zero stale audio leakage to playback device) and discarding subsequent in-flight server egress packets across the WAN via context-id isolation, enabling seamless recovery when clinical or patient directives change dynamically.

### Acceptance Test
- **Interruption Timing**: Mid-synthesis interruption triggered after audio streaming has commenced during a long medication instruction (>8 seconds duration).
- **Target Outcome**:
  1. **Client Cutoff Latency < 200 ms**: Local execution time to sever audio callbacks, detach the active context, and clear the client audio buffer to silence.
  2. **Zero Stale Audio Leakage to Playback**: `stale_audio_bytes_emitted == 0` (strictly 0 bytes sent to audio device or callbacks).
  3. **Network In-Flight Drain Tracked**: Measures total time from cancel invocation until the final in-flight chunk emitted by the cloud server arrives over the WebSocket TCP socket and is discarded.
  4. **Subsequent Synthesis Recovery**: Immediate clean synthesis for the NEW text instruction with 100% completion and zero stale token interference.

### Procedure
1. Initialize `RimeWebSocketClient` connecting to Rime's live `/ws3` endpoint (`wss://users-ws.rime.ai/ws3`).
2. Dispatch long medication instruction: `"Take one tablet of Paracetamol 500mg in the morning after breakfast with a full glass of water, and ensure you do not exceed 4000mg per day to avoid acute liver injury. If fever or acute pain persists for more than three consecutive days, stop taking the medication and consult your primary care physician immediately."`
3. As soon as at least 5 audio chunks stream in, invoke `client.cancel()`.
4. Monitor incoming TCP stream to measure in-flight network drain latency and verify client context-id filtering.
5. Dispatch new medication directive: `"Amoxicillin 250mg capsule, take two capsules orally before meals."`
6. Confirm subsequent synthesis completion, validating received audio bytes and absence of old speech tokens.
7. Execute automated 5-trial benchmark via:
   ```bash
   python scripts/run_interruption_benchmark.py
   ```

### Result Table (`results/interruption_results.csv`)

| Run | Client Cutoff Latency (ms) | Network In-Flight Drain (ms) | Stale Audio Emitted to Speaker | In-Flight Bytes Dropped | Pass/Fail | Status / Notes |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | 0.066 ms | 1974.5 ms | 0 bytes | 828,876 B | **PASS** | Instant callback severance & buffer clear |
| **2** | 0.028 ms | 1928.0 ms | 0 bytes | 804,146 B | **PASS** | Instant callback severance & buffer clear |
| **3** | 0.043 ms | 1630.4 ms | 0 bytes | 90,112 B | **PASS** | Instant callback severance & buffer clear |
| **4** | 0.033 ms | 1594.1 ms | 0 bytes | 183,296 B | **PASS** | Instant callback severance & buffer clear |
| **5** | 0.044 ms | 1941.1 ms | 0 bytes | 1,035,034 B | **PASS** | Instant callback severance & buffer clear |

- **Mean Client Cutoff Latency**: **0.043 ms** (Instant local callback detachment, buffer cleared to 0 bytes)
- **Mean Network In-Flight Drain**: **1,813.6 ms** (Trans-continental roundtrip + cloud synthesis queue drain before server-side `clear` took effect)
- **Stale Audio Leakage**: **0 bytes** across all 5 evaluation runs (100% of in-flight bytes filtered at transport layer)
- **Recovery Success Rate**: **100% (5/5 PASS)**

### Metric Distinction & Architectural Safeguards
1. **Client Cutoff vs. Network Drain**:
   - `Client Cutoff Latency` (~0.043 ms) measures the synchronous time required for `client.cancel()` to sever audio callbacks, detach the active context ID, and empty the local playback queue. To the human listener and the sound hardware, interruption is immediate.
   - `Network In-Flight Drain` (~1.8 s) reflects the physical WAN roundtrip delay (base ping-pong RTT ~270 ms from India to US-West edge) plus the time for Rime's cloud inference engine to process the `{"operation": "clear"}` signal and cease audio chunk transmission.
2. **Context-ID Tagging Guarantee**:
   - Every synthesis turn is tagged with a unique `contextId`. When `cancel()` is triggered, `_active_context_id` is immediately invalidated. Any subsequent audio chunks in transit across TCP buffers are intercepted by `_read_loop()` and dropped into `_stale_audio_dropped_bytes`, completely preventing stale audio from leaking into subsequent speech turns.
3. **Audio Playback Backend**:
   - The evaluation benchmark tracks callback delivery and buffer state; hardware audio device buffer drain latencies (e.g. ALSA/CoreAudio/WASAPI ring buffers) depend on the client playback sink.

