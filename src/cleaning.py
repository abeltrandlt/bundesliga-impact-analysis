from __future__ import annotations
from typing import Dict, List
import pandas as pd
import numpy as np
import re
from .utils import load_yaml, ensure_dir, get_logger

logger = get_logger()

# ------------ Config -------------
RAW_PATH = "data/raw"
OUT_PATH = "data/processed"
TABLES = ["standard", "shooting", "passing", "possession", "defending"]

# Strategy when players have multiple clubs in a season:
# "total" -> use the player's Total row if present; "club" -> keep club-specific rows (no aggregation)
CLUB_MODE = "total"   # change to "club" if you want club-specific rows

# Minimum minutes to include a player in per-90 analysis (helps remove tiny samples)
MIN_MINUTES = 300

# ------------ Helpers -------------

def _std_name(s: str) -> str:
    if pd.isna(s): return s
    # normalize spacing and case; keep accents (FBref already consistent)
    return re.sub(r"\s+", " ", str(s)).strip()

def _coerce_numeric(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def _strip_suffix_cols(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove any columns already suffixed with _x / _y to prevent merge suffix conflicts.
    If both exist for the same root, keep the non-null-coalesced root.
    """
    import pandas as pd
    roots = {}
    for c in list(df.columns):
        if c.endswith("_x") or c.endswith("_y"):
            root = c[:-2]
            roots.setdefault(root, []).append(c)

    for root, suffs in roots.items():
        # coalesce into plain root if not present
        if root not in df.columns:
            series = pd.Series(index=df.index, dtype="float64")
            if f"{root}_x" in df.columns:
                series = df[f"{root}_x"].combine_first(series)
            if f"{root}_y" in df.columns:
                series = series.combine_first(df[f"{root}_y"])
            df[root] = series
        # drop all suffix versions
        df.drop(columns=[c for c in suffs if c in df.columns], inplace=True, errors="ignore")
    return df

def _has_col(df: pd.DataFrame, c: str) -> bool:
    return c in df.columns

def _derive_nineties(df: pd.DataFrame) -> pd.DataFrame:
    # FBref has "90s" column in Standard; if missing, compute from minutes if available
    if "nineties" not in df.columns:
        if "90s" in df.columns:
            df = df.rename(columns={"90s": "nineties"})
        elif "minutes" in df.columns:
            df["nineties"] = df["minutes"] / 90.0
    return df

def _drop_nonplayers(df: pd.DataFrame) -> pd.DataFrame:
    # Drop rows where player is blank or is an aggregate
    if _has_col(df, "player"):
        m = df["player"].astype(str).str.len() > 0
        df = df[m]
    # FBref sometimes includes rows like "Squad Total" or "Opponent Total"
    for col in ["player","club","squad"]:
        if _has_col(df, col):
            df = df[~df[col].astype(str).str.contains("Total|Opponent", case=False, na=False)]
    return df

def _standardize_common_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "squad": "club",
        "rk": "rk",
        "pos": "position",
        "nation": "nation",
        "age": "age",
        "born": "born",
        "mp": "matches",
        "starts": "starts",
        "min": "minutes",
        "90s": "nineties",
        # attacking
        "gls": "goals",
        "ast": "assists",
        "xg": "xg",
        "xa": "xa",
        # possession/passing (these may vary by table)
        "prog": "prog",  # generic progressive (table-specific)
    }
    # apply if present
    to_apply = {k:v for k,v in rename_map.items() if k in df.columns}
    df = df.rename(columns=to_apply)
    # clean strings
    for col in ["player","club","position"]:
        if _has_col(df, col):
            df[col] = df[col].map(_std_name)
    return df

def _handle_multi_club(df: pd.DataFrame) -> pd.DataFrame:
    """
    FBref may include a player's split rows across clubs plus a 'Total' row.
    - If CLUB_MODE='total': keep the 'Total' row if present, else keep a single club row.
    - If CLUB_MODE='club': drop the 'Total' rows, keep all club-specific rows.
    Works even if 'minutes' is missing.
    """
    if not _has_col(df, "player") or not _has_col(df, "club"):
        return df

    df = df.copy()
    df["is_total"] = df["club"].astype(str).str.contains("Total", case=False, na=False)

    if CLUB_MODE == "total":
        # Prefer Total if present; otherwise keep the first occurrence for that player
        # If minutes exists, use it as a tiebreaker; otherwise don’t.
        has_minutes = "minutes" in df.columns
        sort_by = ["player", "is_total"] + (["minutes"] if has_minutes else [])
        ascending = [True, False] + ([False] if has_minutes else [])
        df = (
            df.sort_values(sort_by, ascending=ascending)
              .drop_duplicates(subset=["player"], keep="first")
        )
        df = df.drop(columns=["is_total"], errors="ignore")
    else:
        # Keep club splits; drop totals
        df = df[~df["is_total"]].drop(columns=["is_total"], errors="ignore")

    return df

def _attach_minutes_from_standard(df: pd.DataFrame, season_str: str) -> pd.DataFrame:
    """Left-join minutes (and 90s if present) from the Standard table onto df."""
    try:
        std = load_table(season_str, "standard")
        std = _standardize_common_columns(std)
        std = _drop_nonplayers(std)
        std = _coerce_numeric(std, ["minutes"])
        std = _handle_multi_club(std)
        cols = [c for c in ["player","club","minutes","nineties","90s"] if c in std.columns]
        std_min = std[cols].copy()
        if "90s" in std_min.columns and "nineties" not in std_min.columns:
            std_min = std_min.rename(columns={"90s": "nineties"})
        # Join on player+club when both exist; fall back to player
        keys = ["player","club"] if {"player","club"}.issubset(df.columns) and {"player","club"}.issubset(std_min.columns) else ["player"]
        return df.merge(std_min.drop_duplicates(subset=keys), on=keys, how="left", suffixes=("", "_std"))
    except Exception as e:
        logger.warning(f"Could not attach minutes from Standard: {e}")
        return df

def _per90(df: pd.DataFrame, base_cols: List[str], minutes_floor: int = MIN_MINUTES) -> pd.DataFrame:
    """
    Create <metric>_per90 columns. Works even if 'minutes' or 'nineties' are missing.
    - If 'nineties' is absent, tries '90s', else derives from 'minutes' (if present).
    - If 'minutes' is absent, skips minutes-based filtering but still computes per-90 if 'nineties' exists.
    """
    df = df.copy()

    # ensure 'nineties'
    if "nineties" not in df.columns:
        if "90s" in df.columns:
            df = df.rename(columns={"90s": "nineties"})
        elif "minutes" in df.columns:
            df["nineties"] = df["minutes"] / 90.0

    # if we still don't have nineties, we can't compute per-90 reliably
    if "nineties" not in df.columns:
        # create the columns but as NaN to keep schema predictable
        for b in base_cols:
            if b in df.columns:
                df[f"{b}_per90"] = np.nan
        return df

    # optional stability filter if minutes exist
    if "minutes" in df.columns:
        df.loc[df["minutes"] < minutes_floor, "nineties"] = np.nan

    for b in base_cols:
        if b in df.columns:
            df[f"{b}_per90"] = df[b] / df["nineties"]
    return df

def _suffix(df: pd.DataFrame, cols: List[str], suff: str) -> pd.DataFrame:
    to_rename = {c: f"{c}{suff}" for c in cols if c in df.columns}
    return df.rename(columns=to_rename)

# ------------ Table-specific loaders -------------

def load_table(season_str: str, table: str) -> pd.DataFrame:
    """
    Reads a player-level CSV from data/raw written by Phase 1.
    Example filenames:
      data/raw/fbref_standard_2025-2026.csv
    """
    path = f"{RAW_PATH}/fbref_{table}_{season_str}.csv"
    df = pd.read_csv(path)
    # Standardize common cols early
    df = _standardize_common_columns(df)
    df = _drop_nonplayers(df)
    # Normalize identifiers
    if "player" not in df.columns:
        # Some tables use 'player' already; if not, bail out early
        logger.warning(f"{table}: no 'player' column after standardization.")
    # Minutes might be missing on some tables; coerce numerics where present
    num_candidates = ["age","minutes","nineties","goals","assists","xg","xa"]
    df = _coerce_numeric(df, [c for c in num_candidates if c in df.columns])
    return df

def load_standard(season_str: str) -> pd.DataFrame:
    df = load_table(season_str, "standard")
    # Standard table typically contains: player, position, club, age, minutes, 90s, gls, ast, xg, xa, etc.
    df = _handle_multi_club(df)
    df = _per90(df, ["goals","assists","xg","xa"])
    keep = [c for c in [
        "player","position","club","age","minutes","nineties",
        "goals","assists","xg","xa",
        "goals_per90","assists_per90","xg_per90","xa_per90"
    ] if c in df.columns]
    return df[keep].copy()

def load_shooting(season_str: str) -> pd.DataFrame:
    df = load_table(season_str, "shooting")
    # Shooting table has columns like: "sh", "sot", "g/sh", "g/sot", "avg_shot_dist", etc.
    # Keep a minimal set and per-90 important ones if minutes/nineties present.
    # Common column names vary; try to map a few typical names.
    rename = {
        "sh": "shots", "sot": "shots_on_target",
        "g_sh": "goals_per_shot", "g_sot": "goals_per_shot_on_target",
        "avg_shot_dist": "avg_shot_dist"
    }
    df = df.rename(columns={k:v for k,v in rename.items() if k in df.columns})
    df = _attach_minutes_from_standard(df, season_str)
    df = _handle_multi_club(df)
    df = _per90(df, ["shots","shots_on_target"])
    keep = [c for c in ["player","club","minutes","nineties",
                        "shots","shots_on_target","avg_shot_dist",
                        "shots_per90","shots_on_target_per90"] if c in df.columns]
    return df[keep].copy()

def load_passing(season_str: str) -> pd.DataFrame:
    df = load_table(season_str, "passing")
    # Passing table often includes 'passes_completed', 'passes_attempted', 'cmp%', 'kp' (key passes), 'xA', 'prog'
    rename = {
        "kp": "key_passes",
        "cmp": "passes_completed",
        "att": "passes_attempted",
        "cmp_%": "pass_completion_pct",
        "prog": "prog_passes"
    }
    # Only rename if there's no naming collision
    for k,v in rename.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k:v})
    df = _attach_minutes_from_standard(df, season_str)
    df = _handle_multi_club(df)
    df = _per90(df, ["key_passes","prog_passes"])
    keep = [c for c in ["player","club","minutes","nineties",
                        "key_passes","prog_passes",
                        "key_passes_per90","prog_passes_per90"] if c in df.columns]
    return df[keep].copy()

def load_possession(season_str: str) -> pd.DataFrame:
    df = load_table(season_str, "possession")
    # Possession table contains progressive carries, touches, take-ons, etc.
    rename = {
        "prog_carries": "prog_carries",
        "touches_att_3rd": "touches_att_3rd",
        "succ": "take_ons_won",
        "att": "take_ons_attempted"
    }
    # Only rename keys that exist
    df = df.rename(columns={k:v for k,v in rename.items() if k in df.columns})
    # Ensure progressive carries column name exists or derive from generic 'prog'
    if "prog_carries" not in df.columns and "prog" in df.columns:
        df = df.rename(columns={"prog": "prog_carries"})
    df = _attach_minutes_from_standard(df, season_str)
    df = _handle_multi_club(df)
    df = _per90(df, ["prog_carries","take_ons_won"])
    keep = [c for c in ["player","club","minutes","nineties",
                        "prog_carries","touches_att_3rd","take_ons_won",
                        "prog_carries_per90","take_ons_won_per90"] if c in df.columns]
    return df[keep].copy()

def load_defending(season_str: str) -> pd.DataFrame:
    df = load_table(season_str, "defending")
    # Defending often contains: tackles, tackles_won, interceptions, blocks, pressures (sometimes in possession/def section)
    # Map common names
    rename = {
        "tkl": "tackles",
        "tkl_w": "tackles_won",
        "int": "interceptions",
        "blocks": "blocks",
        "pressures": "pressures"
    }
    for k,v in rename.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k:v})

    df = _attach_minutes_from_standard(df, season_str)
    df = _handle_multi_club(df)
    df = _per90(df, ["tackles","tackles_won","interceptions","blocks","pressures"])
    keep = [c for c in ["player","club","minutes","nineties",
                        "tackles","tackles_won","interceptions","blocks","pressures",
                        "tackles_per90","tackles_won_per90","interceptions_per90","blocks_per90","pressures_per90"]
            if c in df.columns]
    return df[keep].copy()

# ------------ Build season datasets -------------

def _left_join(base: pd.DataFrame, other: pd.DataFrame, how: str = "left") -> pd.DataFrame:
    """
    Safe left-join on player/club keys:
      - dedup 'other' on keys
      - drop overlapping non-key cols from 'other' (e.g., minutes, nineties)
      - strip any existing *_x / *_y columns from 'base' to avoid suffix conflicts
    """
    # choose keys
    if {"player","club"}.issubset(base.columns) and {"player","club"}.issubset(other.columns):
        keys = ["player","club"]
    elif "player" in base.columns and "player" in other.columns:
        keys = ["player"]
    else:
        return base  # nothing sensible to join on

    # 1) dedup right side on keys
    other_dedup = other.drop_duplicates(subset=keys)

    # 2) drop overlapping non-key columns from right side
    dup_cols = [c for c in other_dedup.columns if c in base.columns and c not in keys]
    if dup_cols:
        other_dedup = other_dedup.drop(columns=dup_cols)

    # 3) strip any *_x / *_y already in base to avoid pandas suffix collision
    base = _strip_suffix_cols(base.copy())

    # 4) merge cleanly (no suffixes needed now)
    return base.merge(other_dedup, on=keys, how=how, copy=False)

def build_season(season_label: str, cfg_path: str = "src/config.yml") -> pd.DataFrame:
    cfg = load_yaml(cfg_path)
    season_str = cfg["seasons"][season_label]
    ensure_dir(OUT_PATH)

    logger.info(f"== Build season analytic dataset: {season_label} ({season_str}) ==")
    std = load_standard(season_str)
    pas = load_passing(season_str)
    sho = load_shooting(season_str)
    pos = load_possession(season_str)
    dfn = load_defending(season_str)

    # Base is standard (ensures core identifiers + minutes)
    df = std.copy()
    for piece, name in [(pas,"passing"), (sho,"shooting"), (pos,"possession"), (dfn,"defending")]:
        if piece is not None and len(piece):
            prev_cols = set(df.columns)
            df = _left_join(df, piece, how="left")
            added = [c for c in df.columns if c not in prev_cols and c not in ["player","club"]]
            logger.info(f"Joined {name}: +{len(added)} cols")

    # Filter by minutes threshold (optional; improves per-90 stability)
    if "minutes" in df.columns:
        before = len(df)
        df = df[df["minutes"] >= MIN_MINUTES]
        logger.info(f"Filter minutes >= {MIN_MINUTES}: {before} → {len(df)} rows")

    # Save
    out = f"{OUT_PATH}/players_analytic_{season_str}.csv"
    df.to_csv(out, index=False)
    logger.info(f"Saved → {out} ({len(df)} rows, {df.shape[1]} cols)")
    return df

def build_both(cfg_path: str = "src/config.yml") -> pd.DataFrame:
    """Build live + benchmark and return a combined frame with a 'season' column."""
    cfg = load_yaml(cfg_path)
    live = build_season("live", cfg_path)
    bench = build_season("benchmark", cfg_path)

    live["season"] = cfg["seasons"]["live"]
    bench["season"] = cfg["seasons"]["benchmark"]
    combo = pd.concat([live, bench], ignore_index=True)
    out = f"{OUT_PATH}/players_analytic_combined.csv"
    combo.to_csv(out, index=False)
    logger.info(f"Saved → {out} ({len(combo)} rows)")
    return combo
