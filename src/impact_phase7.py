import pandas as pd

MF_METRICS = [
    "key_passes_per90_pct_role",
    "prog_passes_per90_pct_role",
    "prog_carries_per90_pct_role",
    "interceptions_per90_pct_role"
]

def compute_mf_impact(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["mf_impact_v1"] = out[MF_METRICS].mean(axis=1)

    return out
