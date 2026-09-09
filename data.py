import re

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
    {
        "id": "edge_001",
        "domain": "Pharmacy (Edge Case)",
        "is_edge_case": True,
        "raw_text": "Take Paracetamol 500 mg orally every 6 hours as needed for fever.",
        "expected_pronunciation": "Take Paracetamol five hundred milligram orally every six hours as needed for fever"
    },
]

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
        (r'\bPh:?\s*', 'Phone '),
        (r'\bPh\.?\b', 'Phone'),
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