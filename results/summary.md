# RimeRx TTS Benchmark Summary Report

> **Exploratory &mdash; Small Sample Notice**: Results reported below are generated from exploratory benchmark runs on synthetic domain prescriptions and addresses. Metrics serve as relative performance indicators under provider-recommended configurations.

## Executive Summary

| Provider | Model | Voice | Total Calls | Reliability Rate | Default WER (Mean / Med) | Tuned WER (Mean / Med) | Default PER (Mean) | Tuned PER (Mean) |
|---|---|---|---|---|---|---|---|---|
| **ELEVENLABS** | `elevenlabs` | standard | 6 | 0.0% | N/A | N/A | N/A | N/A |
| **OPENAI** | `openai` | standard | 6 | 0.0% | N/A | N/A | N/A | N/A |
| **RIME** | `rime` | standard | 6 | 100.0% | 93.31% / 94.74% | 65.89% / 74.07% | 92.08% | 0.0% |

## Latency Breakdown (Warm vs Cold Runs)

| Provider | Cold TTFB (Mean) | Warm TTFB (Mean) | Cold Total (Mean) | Warm Total (Mean) |
|---|---|---|---|---|
| **ELEVENLABS** | N/A | N/A | N/A | N/A |
| **OPENAI** | N/A | N/A | N/A | N/A |
| **RIME** | 1312.87 ms | 1405.89 ms | 2641.89 ms | 4199.17 ms |

## Per-Category Error Rate Breakdown

| Category | Total Evaluated | Mean Default WER | Mean Tuned WER | Mean Default PER | Mean Tuned PER | Delta (WER) |
|---|---|---|---|---|---|---|
| `code_switched` | 6 | 96.3% | 81.48% | 85.19% | 0.0% | **-14.82 pts** |
| `dosages` | 6 | 88.89% | 74.07% | 96.3% | 0.0% | **-14.82 pts** |
| `quantities` | 6 | 94.74% | 42.11% | 94.74% | 0.0% | **-52.63 pts** |

## Benchmark Methodology & Caveats

- **ASR Engine**: `faster-whisper` (`small.en`, `int8`, `beam_size=5` for evaluation).

- **Phonetic Distance**: Computed via `epitran` G2P transliteration and Levenshtein phoneme error rate.

- **Audio Files**: Raw audio clips persisted to `results/clips/` for auditory inspection.

