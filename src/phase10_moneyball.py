from __future__ import annotations
import re, unicodedata
import numpy as np
import pandas as pd
from pathlib import Path
from rapidfuzz import process, fuzz


# ---------- Normalization ----------
def _strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))

def norm(s: str) -> str:
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    s = _strip_accents(str(s).lower().strip())
    s = re.sub(r"[^a-z0-9\s\-\.\']", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


# ---------- Valuation snapshot ----------
def build_latest_valuations_asof(players_csv: str, valuations_csv: str, asof_date: str) -> pd.DataFrame:
    players = pd.read_csv(players_csv)
    vals = pd.read_csv(valuations_csv)

    vals["date"] = pd.to_datetime(vals["date"], errors="coerce")
    asof = pd.to_datetime(asof_date)
    vals = vals[vals["date"] <= asof].copy()

    vals = vals.sort_values(["player_id", "date"])
    latest = vals.groupby("player_id", as_index=False).tail(1)

    out = latest.merge(
        players[["player_id", "name", "date_of_birth"]],
        on="player_id",
        how="left"
    ).rename(columns={"name": "tm_name", "market_value_in_eur": "market_value_eur", "date": "value_date"})

    out["market_value_eur"] = pd.to_numeric(out["market_value_eur"], errors="coerce")
    out["tm_name_norm"] = out["tm_name"].map(norm)
    out["dob"] = pd.to_datetime(out["date_of_birth"], errors="coerce")

    return out[["player_id", "tm_name", "tm_name_norm", "dob", "market_value_eur", "value_date"]]


# ---------- Matching FBref -> Transfermarkt ----------
def match_fbref_to_tm_name(
    fb: pd.DataFrame,
    tm: pd.DataFrame,
    fb_player_col: str = "player",
    fb_dob_col: str | None = None,   # if you have born or date of birth in FBref processed
    min_score: int = 92
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Match by normalized name, fuzzy fallback. If fb_dob_col is provided, use DOB to disambiguate when multiple candidates tie.
    Returns matched df and audit df.
    """
    fb = fb.copy()
    tm = tm.copy()

    fb["fb_name_norm"] = fb[fb_player_col].map(norm)

    # Exact name match first
    exact = fb.merge(
        tm[["player_id", "tm_name", "tm_name_norm", "dob", "market_value_eur", "value_date"]],
        left_on="fb_name_norm",
        right_on="tm_name_norm",
        how="left"
    )
    exact["match_type"] = np.where(exact["player_id"].notna(), "exact_name", "unmatched")

    # Fuzzy fallback for unmatched
    choices = tm["tm_name_norm"].dropna().unique().tolist()
    audit_rows = []

    for i, row in exact[exact["player_id"].isna()].iterrows():
        q = row["fb_name_norm"]
        if not q:
            audit_rows.append({"player": row[fb_player_col], "status": "unmatched_empty", "best": None, "score": None})
            continue

        best = process.extractOne(q, choices, scorer=fuzz.token_sort_ratio)
        if not best:
            audit_rows.append({"player": row[fb_player_col], "status": "unmatched", "best": None, "score": None})
            continue

        best_name_norm, score, _ = best
        if score >= min_score:
            # candidate row
            cand = tm[tm["tm_name_norm"] == best_name_norm].iloc[0]
            exact.at[i, "player_id"] = cand["player_id"]
            exact.at[i, "tm_name"] = cand["tm_name"]
            exact.at[i, "dob"] = cand["dob"]
            exact.at[i, "market_value_eur"] = cand["market_value_eur"]
            exact.at[i, "value_date"] = cand["value_date"]
            exact.at[i, "match_type"] = f"fuzzy_{score}"
            audit_rows.append({"player": row[fb_player_col], "status": "fuzzy_matched", "best": cand["tm_name"], "score": score})
        else:
            exact.at[i, "match_type"] = f"unmatched_best_{score}"
            audit_rows.append({"player": row[fb_player_col], "status": "unmatched_low_score", "best": best_name_norm, "score": score})

    audit = pd.DataFrame(audit_rows)
    exact = exact.drop(columns=["fb_name_norm", "tm_name_norm"])
    return exact, audit


# ---------- Manual overrides ----------
def apply_manual_values(df: pd.DataFrame, csv_path: str = "data/manual/manual_market_values.csv") -> pd.DataFrame:
    path = Path(csv_path)
    if not path.exists():
        return df
    ovr = pd.read_csv(path)
    req = {"player", "club", "market_value_eur"}
    if not req.issubset(ovr.columns):
        raise ValueError(f"manual values must include columns: {req}")

    out = df.copy()
    ovr["market_value_eur"] = pd.to_numeric(ovr["market_value_eur"], errors="coerce")

    out = out.merge(
        ovr[["player", "club", "market_value_eur"]].rename(columns={"market_value_eur": "mv_manual"}),
        on=["player", "club"],
        how="left"
    )
    out["market_value_eur"] = out["mv_manual"].combine_first(out["market_value_eur"])
    out = out.drop(columns=["mv_manual"])
    return out


# ---------- Efficiency ----------
def add_value_efficiency(df: pd.DataFrame, impact_col: str) -> pd.DataFrame:
    out = df.copy()
    out["mv_log"] = np.log1p(out["market_value_eur"])
    out["value_eff"] = out[impact_col] / out["mv_log"]
    return out


def make_watchlist(df: pd.DataFrame, role_col: str, metric: str, top_n: int = 20) -> pd.DataFrame:
    out = []
    for role in sorted(df[role_col].dropna().unique()):
        sub = df[df[role_col] == role].copy()
        sub = sub.dropna(subset=[metric])
        out.append(sub.sort_values(metric, ascending=False).head(top_n))
    return pd.concat(out, ignore_index=True)
