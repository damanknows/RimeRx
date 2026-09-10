# RimeRx System Architecture & Pipeline

> **End-to-End Voice Safety Pipeline for Indian Medication Instructions**

```mermaid
flowchart TD
    subgraph Client ["Frontend Layer (static/index.html)"]
        UI["Dark SaaS Web Interface"]
        BtnSpeak["[ Speak with Rime ]"]
        BtnCompare["[ Compare Raw vs RimeRx ]"]
        BtnStress["[ Run Stress Test ]"]
    end

    subgraph Server ["FastAPI Backend Engine (main.py)"]
        API_Config["GET /api/config"]
        API_Render["POST /api/render"]
        API_Eval["POST /api/evaluate"]
        API_WER["POST /api/wer"]
        API_Stress["POST /api/stress/run"]
    end

    subgraph SafetyPipeline ["Voice Safety Engine (data.py)"]
        Extract["1. Critical Entity Extractor"]
        Normalize["2. Normalizer (tune_for_rime)"]
        Validate["3. Semantic Preservation Checker"]
        SafeWrapper["4. Safe Tune Wrapper"]
    end

    subgraph Synthesis ["TTS Provider Layer (tts/providers.py)"]
        Rime["Primary: Rime TTS (mist/v1, marsh, en-IN)"]
        Fallback["Fallback: OpenAI / ElevenLabs"]
        Reliability["Reliability Tracker (TTFB, Warm/Cold)"]
    end

    subgraph Verification ["ASR Benchmark Engine (asr.py)"]
        Whisper["Whisper ASR (small.en, int8, beam=5)"]
        JiWER["WER & PER Evaluator (jiwer)"]
        EntityRecall["Entity Recall Checker"]
    end

    UI -->|1. Prescription Text| API_Render
    API_Render --> Extract
    Extract --> Normalize
    Normalize --> Validate
    Validate -->|Valid| SafeWrapper
    SafeWrapper --> Rime
    Rime -->|Stream MP3| UI
    Rime -->|Failure| Fallback
    Rime --> Reliability
    API_Render --> Whisper
    Whisper --> JiWER
    Whisper --> EntityRecall
    JiWER --> UI
    EntityRecall --> UI
```

## Pipeline Component Description

1. **Frontend Layer (`static/index.html`)**: Dark-themed interactive interface providing real-time audio playback, side-by-side Before/After audio evaluation, active Rime configuration display, and stress test batch runner.
2. **FastAPI Backend (`main.py`)**: REST endpoints serving speech synthesis, audio streaming, evaluation metrics, and benchmark management.
3. **Voice Safety Engine (`data.py`)**: Deterministic regex-based entity extractor and `tune_for_rime` speech normalizer. Enforces `validate_semantic_preservation()` to guarantee zero unauthorized number/drug modifications.
4. **TTS Provider Layer (`tts/providers.py`)**: Manages Rime TTS (`mist/v1`, `marsh`, `en-IN`, `mp3`). Implements `synthesize_with_fallback()` with transparent logging (`Rime unavailable — fallback provider active.`) when fallbacks are enabled.
5. **ASR Benchmark Engine (`asr.py`)**: Closed-loop verification using `faster-whisper` (`small.en`) to transcribe synthesized audio and compute Critical Token Accuracy, WER, and PER.
