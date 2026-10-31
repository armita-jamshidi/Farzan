from data.fetch_translations import anchor_chain, drop_marks, english_quality, join_lines


def test_join_lines_undoes_hyphenation():
    assert join_lines(["complaining of separa-", "tions"]) == "complaining of separations"


def test_drop_marks_removes_stray_numbers():
    assert drop_marks("I consorted 5 with the unhappy") == "I consorted with the unhappy"


def test_persian_ocr_noise_scores_low():
    assert english_quality("Listen to the reed how it tells a tale") > 0.9
    assert english_quality("Hrt& (50 ls SY Ose 3g) sails. lG wah Us") < 0.6


def test_anchor_chain_ignores_misreads_and_finds_books():
    # verse numbers every 5 paragraphs, a stray page number (264), then a new book
    book1 = [(k * 5 + 4, k * 5 + 5) for k in range(110)]  # verses 5..550
    raw = book1[:2] + [(12, 264)] + book1[2:] + [(600, 5), (605, 10)]
    anchors, starts = anchor_chain(raw, 2)
    assert (12, 264) not in anchors
    assert starts == [0, len(anchors) - 2]
