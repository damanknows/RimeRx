# RimeRx — 4-5 Minute Judge Demo Script

> **Voice Safety for Indian Medication Instructions via Rime TTS**

---

## Demo Overview
- **Target Audience**: Hackathon Judges / Evaluators
- **Target Duration**: 4 to 5 Minutes
- **Core Narrative**: Demonstrate how RimeRx solves dangerous mispronunciations and dosage ambiguities in Indian pharmacy prescriptions through deterministic prompt tuning with Rime TTS.

---

## Minute-by-Minute Walkthrough

### 0:00 - 0:45 | 1. The Hard Voice Problem & Pitch
- **Action**: Open the application at `http://localhost:8000`.
- **Speech**:
  > *"In Indian telehealth and e-pharmacy delivery, voice instructions are vital for patient adherence—especially for millions of patients who rely on audio confirmations over small phone screens. But standard TTS engines mangle prescriptions. When given `Tab Augmentin 625mg 1-0-1 x 5 days`, generic models read `1-0-1` as `one hundred and one`, creating a fatal 100x dosage error. RimeRx is a voice safety layer built for Rime TTS that eliminates these mispronunciations with zero latency overhead."*

---

### 0:45 - 1:45 | 2. Live Synthesis & Active Rime Configuration
- **Action**: Highlight the **Active Rime Configuration** card on the dashboard.
- **Speech**:
  > *"Notice our active TTS provider card. Rime is our primary and default speech engine. We are connected to Rime's low-latency `mist/v1` model using the `marsh` speaker with `en-IN` Indian English pronunciation at `https://users.rime.ai/v1/rime-tts`. All API credentials are secured server-side."*
- **Action**: Select the benchmark case `Tab Augmentin 625mg 1-0-1 x 5 days` and click **[ Speak with Rime ]**.
- **Speech**:
  > *"Listen to how clear RimeRx speaks: 'Tablet Augmentin. Six two five milligram. One zero one. For five days.' Every critical token is distinct and unambiguous."*

---

### 1:45 - 2:45 | 3. Raw Rime vs RimeRx Side-by-Side Comparison
- **Action**: Click **[ Compare Raw vs RimeRx ]**.
- **Speech**:
  > *"Now let's compare raw Rime directly against RimeRx side-by-side. 
  > On the left, raw Rime reads the raw prescription text—converting '1-0-1' into 'one hundred and one' and '625mg' into 'six hundred twenty five'. 
  > On the right, RimeRx normalizes the text for the ear while strictly preserving semantics: '1-0-1' becomes 'one zero one', and '625mg' becomes 'six two five milligram'.
  > Below, you see our closed-loop Whisper ASR metrics: Critical Token Accuracy improves from 60% to 100%, WER drops from 35% to 0%, with zero penalty on latency."*

---

### 2:45 - 3:45 | 4. Adversarial Stress Test Suite
- **Action**: Scroll down to the **Stress Test** component. Select case `stress_011` (`Tab Metformin/Glimepiride 500/2 mg 1-0-1 x 30 days`) or click **[ Run All Cases ]**.
- **Speech**:
  > *"Prescriptions aren't always clean. Our 15-case adversarial stress corpus tests combination drugs, subcutaneous insulin units, and complex fraction dosages. Watch as we execute closed-loop TTS-to-ASR verification live. Notice our honest failure handling: if an acoustic ASR model mishears a niche brand name like 'Deriphyllin', RimeRx flags the exact entity misheard instead of fabricating success."*

---

### 3:45 - 4:30 | 5. Evidence & Reproducibility
- **Action**: Point out the **Benchmark Dashboard** and `RIME_EVIDENCE.md` document.
- **Speech**:
  > *"Every claim in RimeRx is backed by reproducible evidence. Running `python run_benchmark.py --mode full` executes all 55 test cases across raw Rime and RimeRx, generating full WER, PER, and entity recall reports in `RIME_EVIDENCE.md`. Our automated test suite includes 342 unit tests verifying semantic preservation, entity extraction, and fallback disclosure."*

---

### 4:30 - 5:00 | 6. Wrap Up & Q&A
- **Speech**:
  > *"RimeRx demonstrates that prompt-engineering for speech synthesis paired with Rime's ultra-low latency TTS transforms raw prescription text into safe, clear, life-saving voice instructions. Thank you!"*
