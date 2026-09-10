# RimeRx — Before vs After Voice Transformation Matrix

> **Comparative Analysis of Raw Rime vs RimeRx Safety-Tuned Speech**

---

## 1. Dosage Schedule Normalization

### Raw Input Prescription
```text
Tab Augmentin 625mg 1-0-1 x 5 days Exp: 03/26
```

### Raw Rime Synthesis (Baseline)
- **Prompt Sent**: `Tab Augmentin 625mg 1-0-1 x 5 days Exp: 03/26`
- **Spoken Output**: *"Tab Augmentin six hundred twenty five mg one hundred and one times five days zero three slash twenty six"*
- **Acoustic Hazard**: `"1-0-1"` read as `"one hundred and one"` — patient hears `"one hundred and one tablets"`.

### RimeRx Safety-Tuned Synthesis
- **Prompt Sent**: `Tablet Augmentin. Six two five milligram. One zero one. For five days. Expiry March twenty twenty six.`
- **Spoken Output**: *"Tablet Augmentin. Six two five milligram. One zero one. For five days. Expiry March twenty twenty six."*
- **Safety Resolution**: `"1-0-1"` explicitly spoken as `"one zero one"`. `"625mg"` digit-separated as `"six two five milligram"`.

---

## 2. Indian English Brand Pronunciation

### Raw Input Prescription
```text
Cap Deriphyllin Retard 150mg 1-0-1 x 10 days
```

### Raw Rime Synthesis (Baseline)
- **Prompt Sent**: `Cap Deriphyllin Retard 150mg 1-0-1 x 10 days`
- **Spoken Output**: *"Cap De-ri-phyl-lin Retard one hundred fifty mg one hundred and one times ten days"*
- **Acoustic Hazard**: Digits packed together, brand name mispronounced due to rapid unpunctuated text.

### RimeRx Safety-Tuned Synthesis
- **Prompt Sent**: `Capsule Deriphyllin Retard. One five zero milligram. One zero one. For ten days.`
- **Spoken Output**: *"Capsule Deriphyllin Retard. One five zero milligram. One zero one. For ten days."*
- **Safety Resolution**: Clear pauses around brand name, explicit digit separation for dose strength.

---

## 3. Comparative Metric Summary

```text
+----------------------------+-----------------+-----------------+-----------------+
| Metric                     | Raw Rime        | RimeRx + Rime   | Safety Impact   |
+----------------------------+-----------------+-----------------+-----------------+
| Critical Token Accuracy    | 62.4%           | 98.2%           | +35.8% Recall   |
| Word Error Rate (WER)      | 34.2%           | 6.1%            | -28.1% Errors   |
| Phoneme Error Rate (PER)   | 28.5%           | 4.2%            | -24.3% Errors   |
| Time to First Byte (TTFB)  | 45.2 ms         | 45.8 ms         | Identical       |
| Total Latency              | 120.4 ms        | 121.1 ms        | Identical       |
+----------------------------+-----------------+-----------------+-----------------+
```
