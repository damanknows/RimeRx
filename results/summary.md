# RimeRx TTS Benchmark Summary Report

> **Exploratory &mdash; Small Sample Notice**: Results reported below are generated from exploratory benchmark runs on synthetic domain prescriptions and addresses. Metrics serve as relative performance indicators under provider-recommended configurations.

## Executive Summary

| Provider | Model | Voice | Total Calls | Reliability Rate | Default WER (Mean) | Tuned WER (Mean) | Default PER (Mean) | Tuned PER (Mean) | Entity Accuracy (Default / Tuned) |
|---|---|---|---|---|---|---|---|---|---|
| **ELEVENLABS** | `elevenlabs` | standard | 10 | 0.0% | N/A | N/A | N/A | N/A | **N/A** |
| **OPENAI** | `openai` | standard | 10 | 0.0% | N/A | N/A | N/A | N/A | **N/A** |
| **RIME** | `rime` | standard | 10 | 100.0% | 85.34% | 62.68% | 89.83% | 0.0% | **81.58% / 50.84%** |

## Latency Breakdown (Warm vs Cold Runs)

| Provider | Cold TTFB (Mean) | Warm TTFB (Mean) | Cold Total (Mean) | Warm Total (Mean) |
|---|---|---|---|---|
| **ELEVENLABS** | N/A | N/A | N/A | N/A |
| **OPENAI** | N/A | N/A | N/A | N/A |
| **RIME** | 1378.17 ms | 1906.67 ms | 2678.94 ms | 6753.47 ms |

## Per-Category Error Rate Breakdown

| Category | Total Evaluated | Mean Default WER | Mean Tuned WER | Mean Default PER | Mean Tuned PER | Entity Recall (Tuned) | Delta (WER) |
|---|---|---|---|---|---|---|---|
| `code_switched` | 6 | 92.59% | 81.48% | 85.19% | 0.0% | **57.1%** | **-11.11 pts** |
| `dosages` | 12 | 82.18% | 76.16% | 93.98% | 0.0% | **53.55%** | **-6.02 pts** |
| `drug_names` | 6 | 75.0% | 37.5% | 81.25% | 0.0% | **40.0%** | **-37.5 pts** |
| `quantities` | 6 | 94.74% | 42.11% | 94.74% | 0.0% | **50.0%** | **-52.63 pts** |

## Benchmark Methodology & Caveats

- **ASR Engine**: `faster-whisper` (`small.en`, `int8`, `beam_size=5` for evaluation).

- **Phonetic Distance**: Computed via `epitran` G2P transliteration and Levenshtein phoneme error rate.

- **Audio Files**: Raw audio clips persisted to `results/clips/` for auditory inspection.

