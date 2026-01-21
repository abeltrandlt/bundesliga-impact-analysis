import pandas as pd

def load_standard(season="2025-2026"):
    df = pd.read_csv(f"data/raw/fbref_standard_{season}.csv")

    df = df.rename(columns={
        "squad": "club",
        "pos": "position",
        "min": "minutes",
        "90s": "nineties"
    })

    keep_cols = [
        "player",
        "club",
        "position",
        "minutes",
        "nineties"
    ]

    return df[keep_cols]

load_standard()


#Passing Enrichment
def enrich_passing(base: pd.DataFrame, season: str = "2025-2026") -> pd.DataFrame:
    df = pd.read_csv(f"data/raw/fbref_passing_{season}.csv")

    # Canonical names (match your Standard base)
    df = df.rename(columns={
        "squad": "club",
        "pos": "position",
        "90s": "nineties",
        "kp": "key_passes",
        "prgp": "prog_passes",
    })

    # Keep only the columns we need for this enrichment
    keep_raw = ["player", "club", "nineties", "key_passes", "prog_passes"]
    df = df[[c for c in keep_raw if c in df.columns]].copy()

    # Coerce to numeric safely
    for c in ["nineties", "key_passes", "prog_passes"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Per-90 (guard against division by 0)
    df["key_passes_per90"] = df["key_passes"] / df["nineties"].replace({0: pd.NA})
    df["prog_passes_per90"] = df["prog_passes"] / df["nineties"].replace({0: pd.NA})

    # One row per player+club for a clean join
    df = df.drop_duplicates(subset=["player", "club"])

    # Enrichment is left-join: Standard defines existence
    out = base.merge(
        df[["player", "club", "key_passes_per90", "prog_passes_per90"]],
        on=["player", "club"],
        how="left"
    )
    return out


#Shooting Enrichment
def enrich_shooting(base: pd.DataFrame, season: str = "2025-2026") -> pd.DataFrame:
    df = pd.read_csv(f"data/raw/fbref_shooting_{season}.csv")

    # Canonical names
    df = df.rename(columns={
        "squad": "club",
        "pos": "position",
        "90s": "nineties",
        "sh": "shots",
        "xg": "xg",
    })

    # Keep only what we need
    keep_raw = ["player", "club", "nineties", "shots", "xg"]
    df = df[[c for c in keep_raw if c in df.columns]].copy()

    # Coerce to numeric
    for c in ["nineties", "shots", "xg"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Per-90 (guard division)
    df["shots_per90"] = df["shots"] / df["nineties"].replace({0: pd.NA})
    df["xg_per90"] = df["xg"] / df["nineties"].replace({0: pd.NA})

    # One row per player+club
    df = df.drop_duplicates(subset=["player", "club"])

    # Left join: Standard defines existence
    out = base.merge(
        df[["player", "club", "shots_per90", "xg_per90"]],
        on=["player", "club"],
        how="left"
    )
    return out


#Defending Enrichment
def enrich_defending(base: pd.DataFrame, season: str = "2025-2026") -> pd.DataFrame:
    df = pd.read_csv(f"data/raw/fbref_defending_{season}.csv")

    # Canonical names based on YOUR columns
    df = df.rename(columns={
        "squad": "club",
        "pos": "position",
        "90s": "nineties",
        "int": "interceptions",
        "tklw": "tackles_won",
        "clr": "clearances",
        "err": "errors",
        "blocks": "blocks"
    })

    # Keep only what we need for this minimal defending enrichment
    keep_raw = ["player", "club", "nineties", "interceptions", "tackles_won"]
    df = df[[c for c in keep_raw if c in df.columns]].copy()

    # Numeric coercion
    for c in ["nineties", "interceptions", "tackles_won"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Per-90 (guard division)
    df["interceptions_per90"] = df["interceptions"] / df["nineties"].replace({0: pd.NA})
    df["tackles_won_per90"] = df["tackles_won"] / df["nineties"].replace({0: pd.NA})

    # One row per player+club
    df = df.drop_duplicates(subset=["player", "club"])

    # Left join: Standard defines existence
    out = base.merge(
        df[["player", "club", "interceptions_per90", "tackles_won_per90"]],
        on=["player", "club"],
        how="left"
    )
    return out


#Possesion Enrichment
def enrich_possession(base: pd.DataFrame, season: str = "2025-2026") -> pd.DataFrame:
    df = pd.read_csv(f"data/raw/fbref_possession_{season}.csv")

    df = df.rename(columns={
        "squad": "club",
        "pos": "position",
        "90s": "nineties",
        "prgc": "prog_carries",
    })

    keep_raw = ["player", "club", "nineties", "prog_carries"]
    df = df[[c for c in keep_raw if c in df.columns]].copy()

    for c in ["nineties", "prog_carries"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["prog_carries_per90"] = df["prog_carries"] / df["nineties"].replace({0: pd.NA})

    df = df.drop_duplicates(subset=["player", "club"])

    out = base.merge(
        df[["player", "club", "prog_carries_per90"]],
        on=["player", "club"],
        how="left"
    )
    return out



#Runner
def build_player_season_dataset(season: str = "2025-2026") -> pd.DataFrame:
    base = load_standard(season)
    base = enrich_passing(base, season)
    base = enrich_shooting(base, season)
    base = enrich_defending(base, season)
    base = enrich_possession(base, season)
    return base



def save_processed(season: str = "2025-2026"):
    df = build_player_season_dataset(season)
    out_path = f"data/processed/players_base_{season}.csv"
    df.to_csv(out_path, index=False)
    print("Saved:", out_path, "shape:", df.shape)
