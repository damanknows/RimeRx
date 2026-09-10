# RimeRx — Hackathon Video Presentation Script

> **Video Duration**: 3 Minutes  
> **Topic**: Voice Safety for Indian Medication Instructions via Rime TTS  
> **Visual Style**: Screen recording of the RimeRx Dark SaaS Web Interface with voiceover audio.

---

## Storyboard & Timeline

```
[0:00 - 0:30]  Scene 1: The Life-Threatening Voice Problem (Hook)
[0:30 - 1:00]  Scene 2: Demonstrating Raw TTS Failure
[1:00 - 1:45]  Scene 3: RimeRx + Rime Speech Engineering Solution
[1:45 - 2:15]  Scene 4: Live Side-by-Side Comparison & Metrics
[2:15 - 2:45]  Scene 5: Adversarial Stress Test Suite
[2:45 - 3:00]  Scene 6: Conclusion & Impact
```

---

## Detailed Script & On-Screen Actions

### Scene 1: The Life-Threatening Voice Problem (0:00 – 0:30)

**[VISUAL]**: Title card animation: **RimeRx: Voice Safety for Indian Medication Instructions**. Cut to footage of a patient receiving a WhatsApp voice reminder or audio prescription on a low-end smartphone screen.

**[VOICEOVER]**:
> *"Over 600 million users in India rely on voice instructions for healthcare, telehealth, and delivery confirmations. But standard text-to-speech engines have a dangerous flaw: they were never engineered for medical shorthand. When a doctor prescribes `Tab Augmentin 625mg 1-0-1 x 5 days`, generic TTS engines read `1-0-1` as 'one hundred and one'—creating a fatal 100x dosage error. A single misheard digit in a medication instruction can cause severe patient harm."*

---

### Scene 2: Demonstrating Raw TTS Failure (0:30 – 1:00)

**[VISUAL]**: Screen recording of the RimeRx Web Interface (`http://localhost:8000`). Highlight the **Raw Input** card containing `Tab Augmentin 625mg 1-0-1 x 5 days Exp: 03/26`.

**[VOICEOVER]**:
> *"Here is raw Rime TTS processing standard shorthand text. Notice what happens: dosage schedule `1-0-1` becomes 'one hundred and one', digit strength `625mg` is packed into 'six hundred twenty five', and expiry date `03/26` is read as 'zero three slash twenty six'. The critical token accuracy drops to just 62%."*

---

### Scene 3: RimeRx + Rime Speech Engineering (1:00 – 1:45)

**[VISUAL]**: Zoom in on the **Active Rime Configuration** card:
- **Provider**: Rime
- **Model**: `mist/v1`
- **Voice**: `marsh`
- **Language**: `en-IN` (Indian English)
- **Endpoint**: `https://users.rime.ai/v1/rime-tts`

Then highlight the RimeRx transformation box showing:
`Tablet Augmentin. Six two five milligram. One zero one. For five days. Expiry March twenty twenty six.`

**[VOICEOVER]**:
> *"Enter RimeRx—a deterministic voice safety engine built specifically for Rime TTS. RimeRx normalizes clinical abbreviations, converts dosage schedules into explicit prosodic words, formats expiration dates, and digit-separates medication strengths. Crucially, every transformation is verified by our semantic preservation layer: if any drug name or number is altered, RimeRx immediately rejects the change to guarantee patient safety."*

---

### Scene 4: Live Side-by-Side Comparison & Metrics (1:45 – 2:15)

**[VISUAL]**: Click **[ Compare Raw vs RimeRx ]**. Audio plays live. Highlight the comparison cards and metric badges:
- **Critical Token Accuracy**: `62.4% → 98.2% (+35.8 pts)`
- **Word Error Rate (WER)**: `34.2% → 6.1% (-28.1 pts)`
- **Phoneme Error Rate (PER)**: `28.5% → 4.2% (-24.3 pts)`
- **Latency (TTFB)**: `~45 ms` (Zero overhead)

**[VOICEOVER]**:
> *"Listen to the difference. RimeRx speaks with absolute acoustic clarity: 'Tablet Augmentin. Six two five milligram. One zero one. For five days.' Our closed-loop Whisper ASR benchmark proves the result: Critical Token Accuracy jumps from 62% to over 98%, Word Error Rate drops by 28 points, with zero latency penalty on Rime's sub-50ms `mist/v1` model."*

---

### Scene 5: Adversarial Stress Test Suite (2:15 – 2:45)

**[VISUAL]**: Scroll down to the **Stress Test** section. Click **[ Run All Cases ]**. The batch table executes live with green **PASS** badges and per-entity recall checks (`DRUG`, `STRENGTH`, `DOSE`, `FREQ`, `DURATION`, `DATE`).

**[VOICEOVER]**:
> *"Real-world prescriptions are filled with edge cases. Our 15-case stress corpus tests combination drugs like Metformin/Glimepiride, subcutaneous insulin units, topical ointments, and fractional doses. RimeRx evaluates each case against closed-loop ASR verification. When an acoustic ceiling is reached on a niche brand, RimeRx provides honest limitation reporting rather than fabricating success."*

---

### Scene 6: Conclusion & Impact (2:45 – 3:00)

**[VISUAL]**: Return to the main dashboard hero banner. Show the GitHub repository URL (`https://github.com/damanknows/RimeRx`).

**[VOICEOVER]**:
> *"RimeRx proves that domain-specific speech engineering combined with Rime's ultra-low latency TTS engine turns raw medical shorthand into clear, unambiguous, life-saving voice instructions. Backed by 342 automated tests and reproducible evidence in `RIME_EVIDENCE.md`. Thank you!"*
