from prosody.normalize import normalize, tokenize


def test_arabic_yeh_and_kaf_become_persian():
    assert normalize("كتاب علي") == "کتاب علی"


def test_diacritics_removed():
    assert normalize("کز نِیِستان تا مرا بُبْریده‌اند", zwnj="space") == "کز نیستان تا مرا ببریده اند"


def test_zwnj_modes():
    assert normalize("می‌کند") == "میکند"
    assert normalize("می‌کند", zwnj="space") == "می کند"
    assert normalize("می‌کند", zwnj="keep") == "می‌کند"


def test_heh_with_hamza_and_digits():
    assert normalize("خانۀ ۱۲") == "خانه 12"


def test_punctuation_and_spaces():
    assert tokenize("  بشنو، این نی!  ") == ["بشنو", "این", "نی"]


def test_recognizer_and_reference_agree():
    reference = "بشنو این نی چون شکایت می‌کند"
    asr_output = "بشنو اين ني چون شكايت ميكند"
    assert normalize(reference) == normalize(asr_output)
