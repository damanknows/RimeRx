import json, os, sys
base_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, base_dir)
from data import tune_for_rime
pharmacy_path = os.path.join(base_dir, "corpus", "pharmacy.json")

# Define template categories
drugs_list = [
    "Augmentin", "Azithral", "Paracetamol", "Dolo", "Pantocid", "Amoxycillin",
    "Cetirizine", "Metformin", "Telmisartan", "Atorvastatin", "Omeprazole",
    "Disprin", "Crocin", "Combiflam", "Gelusil", "Digene", "Zinetac", "Pan-D",
    "Deriphyllin", "Ibuprofen", "Aspirin", "Ciprofloxacin", "Azithromycin", "Amoxicillin"
]

categories = [
    "drug_names", "strengths", "dosage_schedules", "frequency",
    "duration", "dates", "abbreviations", "quantities", "indian_english", "adversarial"
]

difficulties = ["easy", "medium", "hard", "adversarial"]

corpus = []
idx = 1

# Specific required cases
specific_cases = [
    ("rx_synth_001", "drug_names", "easy", "Tab Augmentin 625mg 1-0-1 x 5 days Exp: 03/26"),
    ("rx_synth_002", "strengths", "medium", "Paracetamol 0.5 mg orally twice daily for 3 days"),
    ("rx_synth_003", "strengths", "medium", "Tab Amoxicillin 1250 mg 1-0-1 x 7 days"),
    ("rx_synth_004", "dosage_schedules", "easy", "Tab Dolo 650mg 1-0-1 after meals for 3 days"),
    ("rx_synth_005", "dosage_schedules", "easy", "Cap Pantocid 40mg 0-1-0 before meals x 14 days"),
    ("rx_synth_006", "dosage_schedules", "easy", "Tab Metformin 500mg 1-1-1 x 30 days"),
    ("rx_synth_007", "dosage_schedules", "medium", "Take 1/2 tab Disprin 350mg SOS for headache"),
    ("rx_synth_008", "dates", "medium", "Syp Azithral 200mg/5ml Exp: 03/26 Mfg: Alembic"),
    ("rx_synth_009", "adversarial", "adversarial", "Vitamin B12 1500mcg OD for 30 days Qty: 30 caps"),
    ("rx_synth_010", "adversarial", "adversarial", "H1N1 vaccine 0.5ml single dose Inj Exp: 12/27"),
]

for cid, cat, diff, text in specific_cases:
    corpus.append({
        "id": cid,
        "domain": "Pharmacy",
        "category": cat,
        "difficulty": diff,
        "raw_text": text,
        "expected_pronunciation": tune_for_rime(text),
        "notice": "Synthetic/curated evaluation data for TTS benchmark — Zero real patient data"
    })
    idx += 1

# Generate synthetic items to reach ~250 items
strengths_patterns = ["500mg", "625mg", "250mg", "100mg", "200mg/5ml", "10mg", "20mg", "40mg", "0.5mg", "1250mg", "1500mcg"]
schedules_patterns = ["1-0-1", "0-1-0", "1-1-1", "1-0-0", "0-0-1", "1/2 tab BD", "1 tab OD"]
freq_patterns = ["BD", "OD", "TDS", "QID", "HS", "SOS", "every 6 hours", "twice daily"]
duration_patterns = ["x 3 days", "x 5 days", "for 7 days", "for 14 days", "for 1 month"]
dates_patterns = ["Exp: 03/26", "Exp: 12/27", "Exp: 08/25", "Exp: 10/28", "Exp: 05/26"]
quantities_patterns = ["Qty: 10 tabs", "Qty: 14 caps", "Qty: 30 tablets", "1 bottle", "10 capsules"]
indian_terms = ["Khane ke baad", "Subah shaam", "Paani ke saath", "Khali pet", "Raat ko lene"]

case_counter = len(corpus) + 1
for cat in categories:
    for diff in difficulties:
        for i in range(6): # Generates 10 * 4 * 6 = 240 additional items
            drug_name = drugs_list[(case_counter) % len(drugs_list)]
            str_val = strengths_patterns[(case_counter) % len(strengths_patterns)]
            sched_val = schedules_patterns[(case_counter) % len(schedules_patterns)]
            freq_val = freq_patterns[(case_counter) % len(freq_patterns)]
            dur_val = duration_patterns[(case_counter) % len(duration_patterns)]
            date_val = dates_patterns[(case_counter) % len(dates_patterns)]
            qty_val = quantities_patterns[(case_counter) % len(quantities_patterns)]
            ind_val = indian_terms[(case_counter) % len(indian_terms)]

            if cat == "drug_names":
                txt = f"Tab {drug_name} {str_val} {sched_val} {dur_val}"
            elif cat == "strengths":
                txt = f"{drug_name} {str_val} orally {freq_val} {dur_val}"
            elif cat == "dosage_schedules":
                txt = f"Tab {drug_name} {str_val} {sched_val} after meals"
            elif cat == "frequency":
                txt = f"Syp {drug_name} {str_val} {freq_val} {dur_val}"
            elif cat == "duration":
                txt = f"Cap {drug_name} {str_val} {freq_val} {dur_val}"
            elif cat == "dates":
                txt = f"Tab {drug_name} {str_val} {sched_val} {date_val}"
            elif cat == "abbreviations":
                txt = f"Tab. {drug_name} {str_val} BD. Mfg: Sun Pharma. {date_val}"
            elif cat == "quantities":
                txt = f"Cap {drug_name} {str_val} {freq_val} {qty_val}"
            elif cat == "indian_english":
                txt = f"Tab {drug_name} {str_val} {sched_val} {ind_val}"
            else: # adversarial
                txt = f"Cap {drug_name} {str_val} {sched_val} {ind_val} {qty_val} {date_val}"

            item = {
                "id": f"rx_synth_{case_counter:03d}",
                "domain": "Pharmacy",
                "category": cat,
                "difficulty": diff,
                "raw_text": txt,
                "expected_pronunciation": tune_for_rime(txt),
                "notice": "Synthetic/curated evaluation data for TTS benchmark — Zero real patient data"
            }
            corpus.append(item)
            case_counter += 1

print(f"Generated {len(corpus)} synthetic pharmacy test items.")
with open(pharmacy_path, "w", encoding="utf-8") as f:
    json.dump(corpus, f, indent=2)

print(f"Saved expanded corpus to {pharmacy_path}")
