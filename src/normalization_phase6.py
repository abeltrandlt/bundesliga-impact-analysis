import pandas as pd
import numpy as np

def add_role_percentiles(df: pd.DataFrame, metrics: list) -> pd.DataFrame:
    out = df.copy()

    for m in metrics:
        pct_col = f"{m}_pct_role"
        out[pct_col] = (
            out
            .groupby("role")[m]
            .rank(pct=True)
        )

    return out
