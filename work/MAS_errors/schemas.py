from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ErrorRecord:
    error_id: str
    dataset: str
    error_type: str
    error_subtype: Optional[str]
    is_dedup: bool

    instance_id: str
    traj_idx: int
    step_idx: int
    chars_before_error: int
    traj_total_chars: int
    traj_total_steps: int

    target: Optional[bool]
    exit_group: Optional[str]
    exit_status: Optional[str]

    error_text: str
    normalized_pattern: Optional[str]
    occurrence_in_traj: Optional[int]

    error_code: Optional[str] = field(default=None)
    error_msg: Optional[str] = field(default=None)
    undefined_name: Optional[str] = field(default=None)
    import_present_in_edit: Optional[bool] = field(default=None)

    def __post_init__(self) -> None:
        if self.step_idx < 0:
            raise ValueError(f"step_idx must be >= 0, got {self.step_idx}")


@dataclass(frozen=True)
class ErrorStats:
    dataset: str
    error_type: str
    error_subtype: Optional[str]
    is_dedup: bool

    n_errors: int
    n_trajectories_total: int
    n_trajectories_with_error: int

    p_trajectory: float
    p_trajectory_ci_lower: float
    p_trajectory_ci_upper: float

    p_per_step: float
    step_mean: float
    step_median: float
    step_std: float

    chars_mean: Optional[float]
    chars_median: Optional[float]

    target_true_n: Optional[int]
    target_false_n: Optional[int]
    exit_success_n: Optional[int]
    exit_limit_hit_n: Optional[int]
    exit_failed_n: Optional[int]

    data_hash: str
    parser_version: str


@dataclass(frozen=True)
class StudySpec:
    study_id: str
    parquet_path: str

    dataset: str
    error_type: str
    error_subtype: Optional[str]
    is_dedup: bool
    subgroup: Optional[str]
    analysis_var: str


@dataclass
class StudyResult:
    study_id: str
    dataset: str
    error_type: str
    error_subtype: Optional[str]
    is_dedup: bool
    subgroup: Optional[str]
    analysis_var: str
    n_errors: int

    status: str
    final_dist: Optional[str]
    p_final: Optional[float]
    D_obs: Optional[float]

    n_attempts: int
    attempts_log: list[dict] = field(default_factory=list)

    duration_s: float = 0.0
    data_hash: str = ""
