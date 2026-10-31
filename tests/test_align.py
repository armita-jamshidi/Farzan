import numpy as np

from data.align import monotonic_align


def test_identity_alignment():
    sim = np.eye(4) * 0.9
    assert monotonic_align(sim) == [([0], [0]), ([1], [1]), ([2], [2]), ([3], [3])]


def test_skips_untranslated_couplet():
    # Persian couplet 1 has no translation (abridged translations skip verses)
    sim = np.array([[0.9, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.9, 0.0], [0.0, 0.0, 0.9]])
    assert monotonic_align(sim) == [([0], [0]), ([2], [1]), ([3], [2])]


def test_two_couplets_one_english_unit():
    sim = np.array([[0.8], [0.8]])
    assert monotonic_align(sim) == [([0, 1], [0])]
