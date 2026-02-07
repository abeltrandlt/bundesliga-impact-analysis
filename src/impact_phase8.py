import numpy as np
import pandas as pd

# Percentile columns (within-role) that exist from Phase 6
ALL_PCT = [
    "key_passes_per90_pct_role",
    "prog_passes_per90_pct_role",
    "shots_per90_pct_role",
    "xg_per90_pct_role",
    "interceptions_per90_pct_role",
    "tackles_won_per90_pct_role",
    "prog_carries_per90_pct_role",
]

ROLE_CORE_WEIGHTS = {
    "MF": {
        "prog_passes_per90_pct_role": 0.30,
        "prog_carries_per90_pct_role": 0.25,
        "key_passes_per90_pct_role": 0.25,
        "interceptions_per90_pct_role": 0.20,
    },
    "FW": {
        "xg_per90_pct_role": 0.35,
        "shots_per90_pct_role": 0.20,
        "key_passes_per90_pct_role": 0.20,
        "prog_carries_per90_pct_role": 0.25,
    },
    "DF": {
        "interceptions_per90_pct_role": 0.35,
        "tackles_won_per90_pct_role": 0.25,
        "prog_passes_per90_pct_role": 0.25,
        "prog_carries_per90_pct_role": 0.15,
    },
}

def reliability_factor(minutes: pd.Series, m1: int = 900) -> pd.Series:
    """
    Simple linear ramp: 0 at 0 min, 1 at m1 min (clipped).
    This is intentionally conservative and easy to explain.
    """
    x = pd.to_numeric(minutes, errors="coerce").fillna(0).astype(float)
    return (x / float(m1)).clip(lower=0, upper=1)

def weighted_sum(df: pd.DataFrame, weights: dict) -> pd.Series:
    cols = list(weights.keys())
    w = np.array([weights[c] for c in cols], dtype=float)
    X = df[cols].astype(float)
    return (X * w).sum(axis=1)

def mean_of_columns(df: pd.DataFrame, cols: list) -> pd.Series:
    if len(cols) == 0:
        return pd.Series(np.nan, index=df.index)
    return df[cols].astype(float).mean(axis=1)

def compute_role_impacts(
    df: pd.DataFrame,
    core_weight: float = 0.85,
    bonus_weight: float = 0.15,
    m1_minutes: int = 900
) -> pd.DataFrame:
    out = df.copy()

    # Exclude GK for now (no score columns filled)
    out["reliability"] = reliability_factor(out["minutes"], m1=m1_minutes)

    # Initialize score columns
    out["impact_core"] = np.nan
    out["impact_bonus"] = np.nan
    out["impact_raw"] = np.nan
    out["impact_adj"] = np.nan

    for role, core_w in ROLE_CORE_WEIGHTS.items():
        mask = out["role"] == role

        # Core score: weighted sum of core percentile metrics
        core = weighted_sum(out.loc[mask], core_w)

        # Bonus score: average of non-core percentile metrics (still within-role percentiles)
        core_cols = set(core_w.keys())
        bonus_cols = [c for c in ALL_PCT if c not in core_cols]

        bonus = mean_of_columns(out.loc[mask], bonus_cols)

        raw = core_weight * core + bonus_weight * bonus
        adj = raw * out.loc[mask, "reliability"]

        out.loc[mask, "impact_core"] = core
        out.loc[mask, "impact_bonus"] = bonus
        out.loc[mask, "impact_raw"] = raw
        out.loc[mask, "impact_adj"] = adj

    return out
