import pandas as pd
import pytest

from work.MAS_errors.utils import filter_subgroup, get_subgroups


@pytest.fixture
def nebius_df():
    return pd.DataFrame({
        "exit_group": ["success", "success", "success", "limit_hit", "failed", "success"],
        "target":     [True,      False,     True,      None,        None,     None],
        "step_idx":   [5,         10,        3,         15,          20,       8],
    })


def test_filter_all(nebius_df):
    assert len(filter_subgroup(nebius_df, "all")) == 6


def test_filter_success_targetT(nebius_df):
    assert len(filter_subgroup(nebius_df, "success_targetT")) == 2


def test_filter_success_targetF(nebius_df):
    assert len(filter_subgroup(nebius_df, "success_targetF")) == 1


def test_filter_limit_hit(nebius_df):
    assert len(filter_subgroup(nebius_df, "limit_hit")) == 1


def test_filter_failed(nebius_df):
    assert len(filter_subgroup(nebius_df, "failed")) == 1


def test_filter_unknown_raises(nebius_df):
    with pytest.raises(ValueError, match="Unknown subgroup"):
        filter_subgroup(nebius_df, "unknown_subgroup")


def test_get_subgroups_nebius(nebius_df):
    subs = get_subgroups(nebius_df)
    assert "success_targetT" in subs
    assert "success_targetF" in subs
    assert "limit_hit" in subs
    assert "failed" in subs


def test_get_subgroups_other_dataset():
    df = pd.DataFrame({"step_idx": [1, 2, 3]})
    assert get_subgroups(df) == ["all"]


def test_get_subgroups_empty():
    df = pd.DataFrame({"exit_group": [], "target": []})
    assert get_subgroups(df) == ["all"]


def test_get_subgroups_partial_target():
    df = pd.DataFrame({
        "exit_group": ["success", "success"],
        "target":     [False, False],
        "step_idx":   [1, 2],
    })
    subs = get_subgroups(df)
    assert "success_targetT" in subs
    assert "success_targetF" in subs
