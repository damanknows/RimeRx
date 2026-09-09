import pytest
from data import TEST_CASES, tune_for_rime, num_to_words

@pytest.mark.parametrize("case", TEST_CASES, ids=lambda c: c["id"])
def test_gold_strings_match_exactly(case):
    """Verify all gold strings in data.py match tune_for_rime output exactly."""
    result = tune_for_rime(case["raw_text"])
    assert result == case["expected_pronunciation"]

def test_num_to_words_helper():
    """Verify number-to-words helper for 3+ digits, 100-multiples, and <=2 digits."""
    # 3+ digits digit-by-digit
    assert num_to_words("625") == "six two five"
    assert num_to_words("560076") == "five six zero zero seven six"
    assert num_to_words("98765") == "nine eight seven six five"

    # 3-digit multiples of 100
    assert num_to_words("200") == "two hundred"
    assert num_to_words("500") == "five hundred"

    # <= 2 digits cardinal
    assert num_to_words("5") == "five"
    assert num_to_words("12") == "twelve"
    assert num_to_words("26") == "twenty six"

def test_dosage_schedule_rule():
    """Verify dosage schedule rule converts '1-0-1' to 'one zero one' (not '1 to 0 to 1')."""
    assert tune_for_rime("1-0-1") == "one zero one"
    assert tune_for_rime("1-1") == "one one"
    assert tune_for_rime("1-0-0") == "one zero zero"

def test_date_rule_before_slash_rule():
    """Verify date rule converts 'Exp: 03/26' to 'Expiry March twenty six' (not '0 3 per 2 6')."""
    assert tune_for_rime("Exp: 03/26.") == "Expiry March twenty six"

def test_slash_rule():
    """Verify slash rule converts '12/3' to 'twelve slash three' and 'mg/ml' to 'milligram per milliliter'."""
    assert tune_for_rime("12/3") == "twelve slash three"
    assert tune_for_rime("200mg/5ml") == "two hundred milligram per five milliliter"

def test_unit_regex_fix_and_splitting():
    """Verify unit regex splitting '625mg' -> 'six two five milligram' without character-class bugs."""
    assert tune_for_rime("625mg") == "six two five milligram"
    assert tune_for_rime("500mg") == "five hundred milligram"
    assert tune_for_rime("5ml") == "five milliliter"
