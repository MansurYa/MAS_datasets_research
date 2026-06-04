import pytest

from work.MAS_errors.utils import wilson_ci


def test_wilson_ci_basic():
    p, lo, hi = wilson_ci(50, 100)
    assert 0.0 <= lo < p < hi <= 1.0
    assert lo < 0.5 < hi


def test_wilson_ci_edge_zero():
    p, lo, hi = wilson_ci(0, 100)
    assert p == 0.0
    assert lo == 0.0
    assert 0.0 < hi < 0.1


def test_wilson_ci_edge_full():
    p, lo, hi = wilson_ci(100, 100)
    assert p == 1.0
    assert lo < 1.0
    assert hi == 1.0


def test_wilson_ci_n_zero():
    p, lo, hi = wilson_ci(0, 0)
    assert p == lo == hi == 0.0


def test_wilson_ci_small_n():
    p, lo, hi = wilson_ci(5, 10)
    assert 0.0 <= lo < p < hi <= 1.0
    assert (hi - lo) > 0.3


def test_wilson_ci_unequal():
    p, lo, hi = wilson_ci(1, 20)
    assert 0.0 <= lo < p < hi <= 1.0
    assert p == 0.05
    assert lo < 0.05 < hi
