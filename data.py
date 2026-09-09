TEST_CASES = [
    {
        "id": "rx_001",
        "domain": "Pharmacy",
        "raw_text": "Tab. Augmentin 625mg 1-0-1 x 5 days. Dr. Reddy's Lab, Hyderabad. Ph: 98765-43210",
        # Gold standard: How it *should* sound (IPA-ish respelling for PER calc)
        "expected_pronunciation": "Tablet Augmentin six two five milligram one zero one times five days Doctor Reddys Lab Hyderabad Phone nine eight seven six five four three two one zero"
    },
    {
        "id": "addr_001",
        "domain": "Delivery",
        "raw_text": "Deliver to: 12/3, 2nd Cross, BTM 2nd Stage, Bengaluru - 560076. Landmark: Near Axis Bank ATM.",
        "expected_pronunciation": "Deliver to twelve slash three second Cross B T M second Stage Bengaluru five six zero zero seven six Landmark Near Axis Bank A T M"
    },
    {
        "id": "rx_002",
        "domain": "Pharmacy",
        "raw_text": "Syp. Azithral 200mg/5ml - 5ml BD. Mfg: Alembic. Exp: 03/26.",
        "expected_pronunciation": "Syrup Azithral two hundred milligram per five milliliter five milliliter twice daily Manufactured by Alembic Expiry March twenty six"
    },
]

# Rime "Writing for the Ear" Ruleset (Deterministic, no LLM latency)
def tune_for_rime(text: str) -> str:
    import re
    # 1. Expand Abbreviations (Pharmacy specific)
    abbr = {
        r'\bTab\.?\b': 'Tablet', r'\bCap\.?\b': 'Capsule', r'\bSyp\.?\b': 'Syrup',
        r'\bInj\.?\b': 'Injection', r'\bBD\b': 'twice daily', r'\bOD\b': 'once daily',
        r'\bTDS\b': 'thrice daily', r'\bMfg\.?\b': 'Manufactured by', r'\bExp\.?\b': 'Expiry',
        r'\bDr\.?\b': 'Doctor', r'\bPh\.?\b': 'Phone', r'\bNo\.?\b': 'Number',
        r'\bx\b': 'times', r'\b/\b': ' per ', r'\b-\b': ' to ',  # ranges
    }
    for k, v in abbr.items():
        text = re.sub(k, v, text, flags=re.IGNORECASE)

    # 2. Spell out Numbers/Dosages (Crucial for Rime)
    # "625mg" -> "six two five m g" (Rime handles "mg" okay, but digits are safer split)
    def split_digits(m): return ' '.join(list(m.group(0)))
    text = re.sub(r'\b\d+\b', split_digits, text) # Standalone numbers
    text = re.sub(r'(\d+)([mg|ml]+)', r'\1 \2', text) # Split 625mg -> 625 mg
    text = re.sub(r'\b(\d{1,2})/(\d{1,2})\b', r'\1 slash \2', text) # Dates 03/26

    # 3. Phonetic Hints for Indian Proper Nouns (Rime "Writing for the ear")
    # Force syllabification for TTS engine
    phonetic_map = {
        'Augmentin': 'Aug-men-tin', 'Azithral': 'A-zith-ral', 'Alembic': 'Al-emb-ic',
        'Hyderabad': 'Hai-de-ra-bad', 'Bengaluru': 'Ben-ga-lu-ru', 'BTM': 'B T M',
        'Axis': 'Ax-is', 'Reddy': 'Red-dy',
    }
    for k, v in phonetic_map.items():
        text = re.sub(rf'\b{k}\b', v, text, flags=re.IGNORECASE)

    # 4. Punctuation for Prosody (Rime respects commas/periods for breathing)
    text = re.sub(r'\.\s*', '. ', text)
    text = re.sub(r',\s*', ', ', text)
    return text.strip()