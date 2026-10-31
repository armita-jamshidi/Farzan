from prosody.meters import MASNAVI_METRE, metre_pattern, split_metre_label


def test_masnavi_pattern():
    # fa'ilatun fa'ilatun fa'ilun
    assert metre_pattern(MASNAVI_METRE) == "-u---u---u-"


def test_split_label():
    feet, name = split_metre_label("مفاعیلن مفاعیلن فعولن (هزج مسدس محذوف یا وزن دوبیتی)")
    assert feet == ["مفاعیلن", "مفاعیلن", "فعولن"]
    assert name == "هزج مسدس محذوف یا وزن دوبیتی"


def test_label_without_name():
    assert metre_pattern("مفتعلن فع مفتعلن فع") == "-uu--" * 2


def test_unknown_foot_returns_none():
    assert metre_pattern("فلان بهمان") is None
    assert metre_pattern("") is None
