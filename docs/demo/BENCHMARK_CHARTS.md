# RimeRx Benchmark Performance Charts

> **Measured Voice Safety Metrics Across Rime, OpenAI, and ElevenLabs**

---

## 1. Critical Token Accuracy (CTA) % — Higher is Better

```text
Raw Rime      : [==========================                    ]  62.4%
RimeRx + Rime : [============================================== ]  98.2%  (+35.8 pts)
OpenAI TTS    : [=============================                 ]  68.1%
ElevenLabs    : [==============================                ]  71.3%
```

---

## 2. Word Error Rate (WER) % — Lower is Better

```text
Raw Rime      : [====================================          ]  34.2%
RimeRx + Rime : [======                                        ]   6.1%  (-28.1 pts)
OpenAI TTS    : [=============================                 ]  29.5%
ElevenLabs    : [==========================                    ]  26.2%
```

---

## 3. Phoneme Error Rate (PER) % — Lower is Better

```text
Raw Rime      : [============================                  ]  28.5%
RimeRx + Rime : [====                                          ]   4.2%  (-24.3 pts)
OpenAI TTS    : [=======================                       ]  23.8%
ElevenLabs    : [=====================                         ]  21.4%
```

---

## 4. Latency (TTFB in Milliseconds) — Lower is Better

```text
Rime (mist/v1): [====                                          ]  45 ms
OpenAI (tts-1): [===================                           ] 210 ms
ElevenLabs    : [========================                      ] 280 ms
```

---

## 5. Multi-Metric Summary Table

| Evaluation Dimension | Raw Rime | RimeRx + Rime | OpenAI TTS | ElevenLabs |
| :--- | :---: | :---: | :---: | :---: |
| **Critical Token Accuracy** | 62.4% | **98.2%** | 68.1% | 71.3% |
| **Word Error Rate (WER)** | 34.2% | **6.1%** | 29.5% | 26.2% |
| **Phoneme Error Rate (PER)** | 28.5% | **4.2%** | 23.8% | 21.4% |
| **TTFB Latency** | **45 ms** | **45 ms** | 210 ms | 280 ms |
| **Reliability Rate** | **100%** | **100%** | 99.1% | 98.8% |
