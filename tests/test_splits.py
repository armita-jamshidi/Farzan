from data.make_splits import assign, unit_of


def _rows(n_units=200, per_unit=5):
    return [
        {"source": "Divan", "book": None, "poem_number": u, "verse_number": v}
        for u in range(1, n_units + 1)
        for v in range(1, per_unit + 1)
    ]


def test_no_unit_on_both_sides():
    splits = assign(_rows(), 0.1, 0.05, 200)
    seen = {}
    for name, part in splits.items():
        for r in part:
            assert seen.setdefault(unit_of(r), name) == name


def test_min_test_size_and_determinism():
    a = assign(_rows(), 0.01, 0.05, 200)
    b = assign(_rows(), 0.01, 0.05, 200)
    assert len(a["test"]) >= 200
    assert a == b


def test_famous_passage_held_out():
    rows = _rows() + [{"source": "Masnavi", "book": 1, "poem_number": 1, "verse_number": 1}]
    splits = assign(rows, 0.1, 0.05, 200)
    assert any(r["source"] == "Masnavi" for r in splits["test"])
