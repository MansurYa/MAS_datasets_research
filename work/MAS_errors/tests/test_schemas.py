import numpy as np
import pytest
from dataclasses import FrozenInstanceError

from work.MAS_errors.schemas import ErrorRecord
from work.MAS_errors.utils import data_hash, df_to_records, records_to_df

_BASE = dict(
    error_id="test_1", dataset="nebius", error_type="invalid_invocation",
    error_subtype="A", is_dedup=False, instance_id="r1", traj_idx=0,
    step_idx=5, chars_before_error=1000, traj_total_chars=5000,
    traj_total_steps=10, target=True, exit_group="success",
    exit_status="submitted", error_text="err", normalized_pattern="p",
    occurrence_in_traj=1,
)


def _rec(**kw) -> ErrorRecord:
    return ErrorRecord(**{**_BASE, **kw})


def test_error_record_immutable():
    r = _rec()
    with pytest.raises(FrozenInstanceError):
        r.step_idx = 99


def test_records_to_df_roundtrip():
    r1 = _rec(error_id="test_1", is_dedup=False)
    r2 = _rec(error_id="test_2", is_dedup=True)
    back = df_to_records(records_to_df([r1, r2]))
    assert len(back) == 2
    assert back[0].error_id == "test_1"
    assert back[0].is_dedup == False
    assert back[1].is_dedup == True
    assert back[0].error_subtype == "A"


def test_data_hash_deterministic():
    arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    h1 = data_hash(arr)
    h2 = data_hash(arr)
    h3 = data_hash([1.0, 2.0, 3.0, 4.0, 5.0])
    assert h1 == h2 == h3
    assert len(h1) == 64


def test_data_hash_different_arrays():
    h1 = data_hash([1.0, 2.0, 3.0])
    h2 = data_hash([1.0, 2.0, 4.0])
    h3 = data_hash([1.0, 2.0])
    assert h1 != h2
    assert h1 != h3
    assert h1 != data_hash([3.0, 2.0, 1.0])


def test_data_hash_empty():
    h = data_hash([])
    assert len(h) == 64
