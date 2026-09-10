import os, json, re
from app.config import CORPUS_DIR

def _load_corpus():
    pharmacy_path = os.path.join(CORPUS_DIR, "pharmacy.json")
    logistics_path = os.path.join(CORPUS_DIR, "logistics.json")

    cases = []
    if os.path.exists(pharmacy_path):
        with open(pharmacy_path, "r", encoding="utf-8") as f:
            cases.extend(json.load(f))
    if os.path.exists(logistics_path):
        with open(logistics_path, "r", encoding="utf-8") as f:
            cases.extend(json.load(f))

    for c in cases:
        if "notice" not in c:
            c["notice"] = "Synthetic/curated evaluation data for TTS benchmark — Zero real patient data"

    if not cases:
        cases = [
            {
                "id": "rx_001",
                "domain": "Pharmacy",
                "category": "dosages",
                "raw_text": "Tab. Augmentin 625mg 1-0-1 x 5 days. Dr. Reddy's Lab, Hyderabad. Ph: 98765-43210",
                "expected_pronunciation": "Tablet Augmentin six two five milligram one zero one times five days Doctor Reddys Lab Hyderabad Phone nine eight seven six five four three two one zero"
            },
            {
                "id": "addr_001",
                "domain": "Delivery",
                "category": "street_addresses",
                "raw_text": "Deliver to: 12/3, 2nd Cross, BTM 2nd Stage, Bengaluru - 560076. Landmark: Near Axis Bank ATM.",
                "expected_pronunciation": "Deliver to twelve slash three second Cross B T M second Stage Bengaluru five six zero zero seven six Landmark Near Axis Bank A T M"
            },
            {
                "id": "rx_002",
                "domain": "Pharmacy",
                "category": "quantities",
                "raw_text": "Syp. Azithral 200mg/5ml - 5ml BD. Mfg: Alembic. Exp: 03/26.",
                "expected_pronunciation": "Syrup Azithral two hundred milligram per five milliliter five milliliter twice daily Manufactured by Alembic Expiry March twenty six"
            },
            {
                "id": "edge_001",
                "domain": "Pharmacy (Edge Case)",
                "category": "quantities",
                "is_edge_case": True,
                "raw_text": "Take Paracetamol 500 mg orally every 6 hours as needed for fever.",
                "expected_pronunciation": "Take Paracetamol five hundred milligram orally every six hours as needed for fever"
            },
        ]
    return cases

TEST_CASES = _load_corpus()

DIGIT_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]

CARDINAL_LESS_THAN_20 = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"
]

TENS_WORDS = {
    20: "twenty", 30: "thirty", 40: "forty", 50: "fifty",
    60: "sixty", 70: "seventy", 80: "eighty", 90: "ninety"
}

MONTH_MAP = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}

ORDINALS = {
    "1st": "first", "2nd": "second", "3rd": "third", "4th": "fourth",
    "5th": "fifth", "6th": "sixth", "7th": "seventh", "8th": "eighth", "9th": "ninth"
}

def num_to_words(num_str: str) -> str:
    """
    Converts a number string to words.
    - Numbers with 3+ digits or phone-like sequences (except 3-digit multiples of 100 like 200, 500) -> digit-by-digit ("625" -> "six two five")
    - 3-digit multiples of 100 -> cardinal ("200" -> "two hundred")
    - Numbers <= 2 digits -> cardinal ("5" -> "five", "12" -> "twelve", "26" -> "twenty six")
    """
    n = int(num_str)
    if len(num_str) <= 2:
        if n < 20:
            return CARDINAL_LESS_THAN_20[n]
        tens = (n // 10) * 10
        rem = n % 10
        if rem == 0:
            return TENS_WORDS[tens]
        return f"{TENS_WORDS[tens]} {CARDINAL_LESS_THAN_20[rem]}"
    else:
        if len(num_str) == 3 and n % 100 == 0:
            hundreds_digit = n // 100
            return f"{CARDINAL_LESS_THAN_20[hundreds_digit]} hundred"
        return " ".join(DIGIT_WORDS[int(d)] for d in num_str)

def cardinal_num_to_words(num_str: str) -> str:
    try:
        n = int(num_str)
        if n < 20:
            return CARDINAL_LESS_THAN_20[n]
        if n < 100:
            tens = (n // 10) * 10
            rem = n % 10
            return TENS_WORDS[tens] if rem == 0 else f"{TENS_WORDS[tens]} {CARDINAL_LESS_THAN_20[rem]}"
        if n < 1000:
            h = n // 100
            rem = n % 100
            rem_str = f" {cardinal_num_to_words(str(rem))}" if rem > 0 else ""
            return f"{CARDINAL_LESS_THAN_20[h]} hundred{rem_str}"
        return " ".join(DIGIT_WORDS[int(d)] for d in num_str if d.isdigit())
    except Exception:
        return " ".join(DIGIT_WORDS[int(d)] for d in num_str if d.isdigit())

def tune_for_rime(text: str) -> str:
    # 1. Expand Abbreviations and Labels
    abbr = [
        (r'\bTab\.?\b', 'Tablet'),
        (r'\bCap\.?\b', 'Capsule'),
        (r'\bSyp\.?\b', 'Syrup'),
        (r'\bInj\.?\b', 'Injection'),
        (r'\bBD\b', 'twice daily'),
        (r'\bOD\b', 'once daily'),
        (r'\bTDS\b', 'thrice daily'),
        (r'\bMfg:?\s*', 'Manufactured by '),
        (r'\bMfg\.?\b', 'Manufactured by'),
        (r'\bExp:?\s*', 'Expiry '),
        (r'\bExp\.?\b', 'Expiry'),
        (r'\bDr\.?\b', 'Doctor'),
        (r'\bPh[:.]\s*', 'Phone '),
        (r'\bPh\b(?=\s*\d)', 'Phone '),
        (r'\bNo\.?\b', 'Number'),
        (r'\bLandmark:\s*', 'Landmark '),
        (r'\bDeliver to:\s*', 'Deliver to '),
        (r'\bx\b', 'times'),
    ]
    for pattern, repl in abbr:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)

    # 2. Acronyms, Possessives, and Ordinals
    text = re.sub(r"(\w+)'s\b", r"\1s", text)

    for acr in ["BTM", "ATM"]:
        text = re.sub(rf'\b{acr}\b', ' '.join(list(acr)), text)

    for ord_key, ord_val in ORDINALS.items():
        text = re.sub(rf'\b{ord_key}\b', ord_val, text, flags=re.IGNORECASE)

    # 3. Dosage schedule rule BEFORE generic hyphen rule
    def replace_dosage(m):
        digits = [m.group(1), m.group(2)]
        if m.group(3):
            digits.append(m.group(3))
        return " ".join(DIGIT_WORDS[int(d)] for d in digits)

    text = re.sub(r'\b(\d)-(\d)(?:-(\d))?\b', replace_dosage, text)

    # 4. Date rule BEFORE generic slash rule
    def replace_date(m):
        month_num = int(m.group(1))
        year_str = m.group(2)
        month_name = MONTH_MAP.get(month_num, f"Month {month_num}")
        return f"{month_name} {num_to_words(year_str)}"

    text = re.sub(r'\b(\d{1,2})/(\d{2})\b', replace_date, text)

    # 5. Units handling (Fix regex bug [mg|ml] -> (?:mg|ml) / (mg|ml))
    # Separate 625mg -> 625 mg, 200mg/5ml -> 200 mg / 5 ml
    text = re.sub(r'(\d+)\s*(mg|ml)\b', r'\1 \2', text, flags=re.IGNORECASE)

    # Expand unit names mg -> milligram, ml -> milliliter
    text = re.sub(r'\bmg\b', 'milligram', text, flags=re.IGNORECASE)
    text = re.sub(r'\bml\b', 'milliliter', text, flags=re.IGNORECASE)

    # 6. Slash rule
    text = re.sub(r'(\d+)/(\d+)', r'\1 slash \2', text)
    text = re.sub(r'\b/\b|(?<=\w)/(?=\w)', ' per ', text)

    # 7. Phone hyphen / generic hyphen cleanup
    text = re.sub(r'(\d{3,})-(\d{3,})', r'\1 \2', text)
    text = re.sub(r'\s+-\s+', ' ', text)
    text = re.sub(r'\b-\b', ' to ', text)

    # 8. Number to words conversion on remaining standalone numbers
    def replace_num(m):
        return num_to_words(m.group(0))

    text = re.sub(r'\b\d+\b', replace_num, text)

    # 9. Clean punctuation & collapse spaces
    text = re.sub(r'[:.,;?!]', '', text)
    text = re.sub(r'\s+', ' ', text)

    return text.strip()

def extract_critical_entities(text: str) -> dict:
    # 1. Abbreviations
    abbr_pattern = r'\b(Tab|Cap|Syp|Inj|Oint|Drops|BD|OD|TDS|QID|HS|SOS|STAT|Exp|Expiry|EXP|Mfg|Qty|Dr|Ph|Rx)\.?'
    found_abbrs = re.findall(abbr_pattern, text, re.IGNORECASE)
    unique_abbrs = []
    seen_abbr_lower = set()
    for a in found_abbrs:
        a_clean = a.strip('.')
        if a_clean.lower() not in seen_abbr_lower:
            seen_abbr_lower.add(a_clean.lower())
            unique_abbrs.append(a_clean)

    # 2. Expiry Date
    expiry_match = re.search(r'\b(?:Exp|Expiry|EXP|EXPDATE)[:.]?\s*(\d{1,2}/\d{2,4})\b', text, re.IGNORECASE)
    expiry = expiry_match.group(1) if expiry_match else None

    # 3. General Date
    date_match = re.search(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)\b', text, re.IGNORECASE)
    date_val = date_match.group(1) if date_match else None

    if not expiry and not date_val:
        slash_date = re.search(r'\b(\d{1,2}/\d{2,4})\b', text)
        if slash_date:
            if "exp" in text.lower():
                expiry = slash_date.group(1)
            else:
                date_val = slash_date.group(1)

    all_dates = re.findall(r'\b\d{1,2}/\d{2,4}\b', text)
    if not expiry and all_dates and "exp" in text.lower():
        expiry = all_dates[0]

    # 5. Drug Name
    known_drugs = [
        "Augmentin", "Azithral", "Paracetamol", "Dolo", "Pantocid", "Amoxycillin",
        "Cetirizine", "Metformin", "Telmisartan", "Atorvastatin", "Omeprazole",
        "Disprin", "Crocin", "Combiflam", "Gelusil", "Digene", "Zinetac", "Pan-D",
        "Deriphyllin", "Ibuprofen", "Aspirin", "Ciprofloxacin", "Azithromycin", "Amoxicillin"
    ]
    drug = None
    for d in known_drugs:
        if re.search(rf'\b{d}\b', text, re.IGNORECASE):
            drug = d
            break
    if not drug:
        prefix_match = re.search(r'\b(?:Tab|Cap|Syp|Inj|Oint|Drops)\.?\s+([A-Z][a-zA-Z0-9\'-]+)', text)
        if prefix_match:
            drug = prefix_match.group(1)

    # 6. Strengths
    strengths = re.findall(r'\b\d+(?:\.\d+)?\s*(?:mg|ml|mcg|gm|iu|%)(?:/\d+(?:\.\d+)?\s*(?:mg|ml|mcg|gm|iu|%))?\b', text, re.IGNORECASE)
    strength = strengths[0] if strengths else None

    # 7. Schedule
    schedule_match = re.search(r'\b(\d\s*-\s*\d(?:\s*-\s*\d)?)\b', text)
    schedule = schedule_match.group(1).replace(' ', '') if schedule_match else None

    # 8. Frequency
    freq_match = re.search(r'\b(BD|OD|TDS|QID|HS|SOS|STAT|once\s+daily|twice\s+daily|thrice\s+daily|every\s+\d+\s+(?:hours|hrs))\b', text, re.IGNORECASE)
    frequency = freq_match.group(1) if freq_match else (schedule if schedule else None)

    # 9. Dose
    dose_match = re.search(r'\b(\d-\d(?:-\d)?|\d+\s*ml|\d+\s*tabs?|\d+\s*tablets?|\d+\s*caps?|\d+\s*puffs?|\d+\s*drops?|1/2\s*tab)\b', text, re.IGNORECASE)
    dose = dose_match.group(1) if dose_match else (schedule if schedule else None)

    # 10. Duration
    duration_match = re.search(r'\b(?:x\s*|for\s*)?(\d+\s*(?:days?|weeks?|months?))\b', text, re.IGNORECASE)
    duration = duration_match.group(1) if duration_match else None

    # 11. Quantity
    qty_match = re.search(r'\b(?:Qty|Quantity)[:.]?\s*(\d+\s*(?:caps?|tabs?|tablets?|capsules?|bottles?)?)\b|\b(\d+\s*(?:caps|tabs|tablets|capsules|bottles))\b', text, re.IGNORECASE)
    quantity = None
    if qty_match:
        quantity = qty_match.group(1) or qty_match.group(2)
        quantity = quantity.strip()

    # Legacy List Fields
    legacy_drugs = [drug] if drug else []
    for d in known_drugs:
        if d not in legacy_drugs and re.search(rf'\b{d}\b', text, re.IGNORECASE):
            legacy_drugs.append(d)

    legacy_schedules = list(set(re.findall(r'\b(?:\d-\d(?:-\d)?|BD|OD|TDS|QID|HS|SOS|STAT|every\s+\d+\s+hours)\b', text, re.IGNORECASE)))
    legacy_dates = all_dates if all_dates else ([date_val] if date_val else [])
    numbers = list(set(re.findall(r'\d+', text)))

    return {
        "drug": drug,
        "strength": strength,
        "dose": dose,
        "frequency": frequency,
        "schedule": schedule,
        "duration": duration,
        "quantity": quantity,
        "date": date_val,
        "expiry": expiry,
        "abbreviations": unique_abbrs,
        "drugs": legacy_drugs,
        "strengths": list(set(strengths)),
        "schedules": legacy_schedules,
        "dates": legacy_dates,
        "numbers": numbers
    }

def extract_pharmacy_entities(text: str) -> dict:
    full = extract_critical_entities(text)
    return {
        "drug": full["drug"],
        "strength": full["strength"],
        "dose": full["dose"],
        "frequency": full["frequency"],
        "schedule": full["schedule"],
        "duration": full["duration"],
        "quantity": full["quantity"],
        "date": full["date"],
        "expiry": full["expiry"],
        "abbreviations": full["abbreviations"]
    }

def check_entity_preservation(entity_type: str, value: str, normalized_text: str) -> bool:
    if not value:
        return True

    norm_lower = normalized_text.lower()
    val_lower = str(value).lower()

    if entity_type == "drug":
        return val_lower in norm_lower

    elif entity_type in ("strength", "quantity", "duration"):
        nums = re.findall(r'\d+', val_lower)
        norm_clean = norm_lower.replace("-", " ").replace(" and ", " ")
        for num_str in nums:
            word_form = num_to_words(num_str).lower().replace("-", " ").replace(" and ", " ")
            cardinal_form = cardinal_num_to_words(num_str).lower().replace("-", " ").replace(" and ", " ")
            digit_words = " ".join(DIGIT_WORDS[int(d)] for d in num_str if d.isdigit())
            if num_str not in normalized_text and word_form not in norm_clean and cardinal_form not in norm_clean and digit_words not in norm_clean:
                return False
        units = re.findall(r'[a-zA-Z]+', val_lower)
        for u in units:
            if u not in ["x", "for", "qty", "exp"] and u not in norm_lower:
                expansions = {
                    "mg": ["milligram", "milligrams", "mg"],
                    "ml": ["milliliter", "milliliters", "ml"],
                    "mcg": ["microgram", "micrograms", "mcg"],
                    "tab": ["tablet", "tablets", "tab"],
                    "tabs": ["tablets", "tablet", "tabs"],
                    "cap": ["capsule", "capsules", "cap"],
                    "caps": ["capsules", "capsule", "caps"],
                    "syp": ["syrup", "syp"],
                    "inj": ["injection", "inj"]
                }
                allowed = expansions.get(u, [u])
                if not any(a in norm_lower for a in allowed):
                    return False
        return True

    elif entity_type in ("dose", "schedule"):
        nums = re.findall(r'\d+', val_lower)
        norm_clean = norm_lower.replace("-", " ").replace(" and ", " ")
        for num_str in nums:
            word_form = num_to_words(num_str).lower().replace("-", " ").replace(" and ", " ")
            cardinal_form = cardinal_num_to_words(num_str).lower().replace("-", " ").replace(" and ", " ")
            digit_words = " ".join(DIGIT_WORDS[int(d)] for d in num_str if d.isdigit())
            if num_str not in normalized_text and word_form not in norm_clean and cardinal_form not in norm_clean and digit_words not in norm_clean:
                return False
        return True

    elif entity_type == "frequency":
        if val_lower in norm_lower:
            return True
        if re.search(r'\d-\d', val_lower):
            nums = re.findall(r'\d+', val_lower)
            digit_words = " ".join(DIGIT_WORDS[int(d)] for d in "".join(nums) if d.isdigit())
            if all(n in norm_lower or num_to_words(n).lower() in norm_lower for n in nums) or digit_words in norm_lower:
                return True
        freq_expansions = {
            "bd": ["twice daily", "twice a day", "two times a day", "bd"],
            "od": ["once daily", "once a day", "one time a day", "od"],
            "tds": ["thrice daily", "three times a day", "tds"],
            "qid": ["four times daily", "four times a day", "qid"],
            "hs": ["at bedtime", "at night", "hs"],
            "sos": ["as needed", "sos"]
        }
        allowed = freq_expansions.get(val_lower, [val_lower])
        return any(a in norm_lower for a in allowed)

    elif entity_type in ("date", "expiry"):
        nums = re.findall(r'\d+', val_lower)
        for num_str in nums:
            word_form = num_to_words(num_str).lower()
            digit_words = " ".join(DIGIT_WORDS[int(d)] for d in num_str if d.isdigit())
            if num_str not in normalized_text and word_form not in norm_lower and digit_words not in norm_lower:
                month_names = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
                if num_str.isdigit() and 1 <= int(num_str) <= 12 and month_names[int(num_str)-1] in norm_lower:
                    continue
                return False
        return True

    return val_lower in norm_lower

def validate_semantic_preservation(raw_text: str, normalized_text: str) -> dict:
    entities = extract_critical_entities(raw_text)
    
    checks = {
        "drug": entities.get("drug"),
        "strength": entities.get("strength"),
        "dose": entities.get("dose"),
        "frequency": entities.get("frequency"),
        "schedule": entities.get("schedule"),
        "duration": entities.get("duration"),
        "quantity": entities.get("quantity"),
        "date": entities.get("date"),
        "expiry": entities.get("expiry")
    }

    unpreserved = []
    preservation_details = {}

    for etype, val in checks.items():
        if val is not None:
            is_preserved = check_entity_preservation(etype, val, normalized_text)
            preservation_details[etype] = {
                "value": val,
                "preserved": is_preserved
            }
            if not is_preserved:
                unpreserved.append(etype)

    raw_numbers = entities["numbers"]
    norm_lower = normalized_text.lower()
    missing_numbers = []
    month_names = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
    for num_str in raw_numbers:
        word_form = num_to_words(num_str).lower()
        digit_words = " ".join(DIGIT_WORDS[int(d)] for d in num_str if d.isdigit())
        if num_str not in normalized_text and word_form not in norm_lower and digit_words not in norm_lower:
            if num_str.isdigit() and 1 <= int(num_str) <= 12 and month_names[int(num_str)-1] in norm_lower:
                continue
            missing_numbers.append(num_str)

    is_safe = (len(unpreserved) == 0) and (len(missing_numbers) == 0)

    return {
        "is_safe": is_safe,
        "is_valid": is_safe,
        "is_preserved": is_safe,
        "status": "SEMANTICS_PRESERVED" if is_safe else "UNSAFE_TRANSFORMATION_REJECTED",
        "unpreserved_entities": unpreserved,
        "missing_numbers": missing_numbers,
        "preservation_details": preservation_details,
        "raw_entities": entities
    }

def safe_tune_for_rime(raw_text: str) -> dict:
    normalized = tune_for_rime(raw_text)
    preservation = validate_semantic_preservation(raw_text, normalized)

    if not preservation["is_safe"]:
        return {
            "is_safe": False,
            "prompt_used": raw_text,
            "normalized_text": normalized,
            "preservation": preservation,
            "error": f"UNSAFE_TRANSFORMATION_REJECTED: Unpreserved entities {preservation['unpreserved_entities']}"
        }

    return {
        "is_safe": True,
        "prompt_used": normalized,
        "normalized_text": normalized,
        "preservation": preservation,
        "error": None
    }

def _load_stress_corpus():
    stress_path = os.path.join(CORPUS_DIR, "stress.json")
    if os.path.exists(stress_path):
        with open(stress_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

STRESS_TEST_CASES = _load_stress_corpus()

def evaluate_stress_case(raw_text: str, hypothesis: str) -> dict:
    entities = extract_critical_entities(raw_text)
    hyp_entities = extract_critical_entities(hypothesis) if hypothesis else {}
    hyp_lower = hypothesis.lower() if hypothesis else ""

    results = {}
    total_present = 0
    matched_count = 0
    failed_fields = []

    field_map = {
        "drug": entities.get("drug"),
        "strength": entities.get("strength"),
        "dose": entities.get("dose") or entities.get("dosage_schedule"),
        "frequency": entities.get("frequency"),
        "duration": entities.get("duration"),
        "date": entities.get("date") or entities.get("expiry")
    }

    heard_map = {
        "drug": hyp_entities.get("drug"),
        "strength": hyp_entities.get("strength"),
        "dose": hyp_entities.get("dose") or hyp_entities.get("dosage_schedule"),
        "frequency": hyp_entities.get("frequency"),
        "duration": hyp_entities.get("duration"),
        "date": hyp_entities.get("date") or hyp_entities.get("expiry")
    }

    for key, val in field_map.items():
        heard_val = heard_map.get(key)
        heard_str = str(heard_val) if heard_val else "(not detected)"
        if val:
            total_present += 1
            is_match = check_entity_preservation(key, str(val), hypothesis)
            if is_match:
                matched_count += 1
                results[key] = {"expected": str(val), "heard": heard_str, "matched": True, "status": "✓ MATCHED"}
            else:
                failed_fields.append(key)
                results[key] = {"expected": str(val), "heard": heard_str, "matched": False, "status": "✗ MISHEARD"}
        else:
            results[key] = {"expected": "N/A", "heard": heard_str, "matched": True, "status": "— NOT IN INPUT"}

    acc_pct = round((matched_count / total_present * 100), 1) if total_present > 0 else 100.0
    overall_matched = (len(failed_fields) == 0)

    limitation_note = None
    if not overall_matched:
        reasons = []
        if "drug" in failed_fields:
            reasons.append(f"ASR acoustic misrecognition on brand name '{entities.get('drug')}' — heard '{heard_map.get('drug', 'nothing')}' instead")
        if "strength" in failed_fields:
            reasons.append(f"Strength specification '{entities.get('strength')}' misheard by acoustic model — heard '{heard_map.get('strength', 'nothing')}' instead")
        if "dose" in failed_fields:
            reasons.append(f"Dosage pattern '{field_map['dose']}' misrecognized in acoustic stream — heard '{heard_map.get('dose', 'nothing')}' instead")
        if "frequency" in failed_fields:
            reasons.append(f"Frequency '{field_map['frequency']}' misheard — heard '{heard_map.get('frequency', 'nothing')}' instead")
        if "duration" in failed_fields:
            reasons.append(f"Duration '{field_map['duration']}' misrecognized — heard '{heard_map.get('duration', 'nothing')}' instead")
        if "date" in failed_fields:
            reasons.append(f"Expiry date format '{field_map['date']}' truncated or misheard — heard '{heard_map.get('date', 'nothing')}' instead")
        limitation_note = "; ".join(reasons) if reasons else f"Entities {failed_fields} misheard by ASR model"

    return {
        "overall_matched": overall_matched,
        "accuracy_pct": acc_pct,
        "matched_count": matched_count,
        "total_count": total_present,
        "failed_fields": failed_fields,
        "entities": results,
        "limitation_note": limitation_note
    }
