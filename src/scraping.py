from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path
import time

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bs4 import BeautifulSoup, Comment
from slugify import slugify

from .utils import load_yaml, ensure_dir, get_logger, polite_pause

logger = get_logger()

# --- helpers to detect/select the correct table (player vs team) ---

def _find_table_html_by_id(soup, table_id: str):
    """Find table HTML by id, scanning both normal DOM and commented blocks (FBref uses comments)."""
    node = soup.find("table", {"id": table_id})
    if node:
        return str(node)
    for c in soup.find_all(string=lambda text: isinstance(text, Comment)):
        if table_id in c:
            frag = BeautifulSoup(c, "lxml")
            node = frag.find("table", {"id": table_id})
            if node:
                return str(node)
    return None

def _flatten_cols(df):
    """Flatten multi-index cols and slugify names."""
    flat = []
    for c in df.columns:
        if isinstance(c, tuple):
            c = c[-1]
        flat.append(slugify(str(c)).replace("-", "_"))
    df.columns = flat
    return df

def _clean_header_rows(df):
    """Drop repeated header rows (FBref repeats 'Rk' rows inside the table body)."""
    firstcol = df.columns[0]
    return df.loc[~df[firstcol].astype(str).str.contains("Rk", na=False)]

def _is_player_table(df) -> bool:
    """Heuristic: player tables have a 'player' column after flattening."""
    cols = {str(c).lower() for c in df.columns}
    return "player" in cols


@dataclass
class TableSpec:
    name: str
    url: str
    html_id: str  # default/fallback id


class FBRefScraper:
    def __init__(self, cfg_path: str = "src/config.yml"):
        self.cfg = load_yaml(cfg_path)
        output = self.cfg.get("output", {})

        # Browser-like default UA; safer than a "Bot/0.1" UA.
        ua = output.get(
            "user_agent",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )

        self.headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Referer": "https://fbref.com/",
        }

        # Deterministic pacing (fixed delay)
        self.pause = float(output.get("request_pause_seconds", 7))

        # Optional: backoff on 403 (recommend 0 if you’re blocked)
        self.retries_on_403 = int(output.get("retries_on_403", 0))
        self.sleep_on_403_seconds = float(output.get("sleep_on_403_seconds", 60))

        self.raw_dir = output.get("raw_dir", "data/raw")
        ensure_dir(self.raw_dir)

        # HTML cache (Playwright output)
        self.html_cache_dir = output.get("html_cache_dir", "data/html_cache")
        self.use_html_cache = bool(output.get("use_html_cache", False))

        # Session + conservative retry for transient errors (429/5xx)
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        retry = Retry(
            total=int(output.get("retries_total", 4)),
            connect=3,
            read=3,
            status=3,
            backoff_factor=float(output.get("retry_backoff_factor", 2.0)),
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.tables = self._load_tables()

    def _load_tables(self) -> List[TableSpec]:
        fb = self.cfg["sources"]["fbref"]
        return [
            TableSpec("standard",   fb["standard"]["url"],   fb["standard"]["table_id"]),
            TableSpec("shooting",   fb["shooting"]["url"],   fb["shooting"]["table_id"]),
            TableSpec("passing",    fb["passing"]["url"],    fb["passing"]["table_id"]),
            TableSpec("possession", fb["possession"]["url"], fb["possession"]["table_id"]),
            TableSpec("defending",  fb["defending"]["url"],  fb["defending"]["table_id"]),
        ]

    def _friendly_pause(self):
        """Deterministic pause."""
        polite_pause(self.pause)

    def _fetch_html(self, url: str, cache_key: str | None = None) -> Optional[str]:
        """
        If use_html_cache is enabled and cache_key is provided, load HTML from:
          {html_cache_dir}/{cache_key}.html

        Otherwise, fall back to a normal network GET (may 403 if Cloudflare challenges you).
        """
        if self.use_html_cache and cache_key:
            cache_path = Path(self.html_cache_dir) / f"{cache_key}.html"
            if cache_path.exists():
                logger.info(f"READ {cache_path}")
                return cache_path.read_text(encoding="utf-8")
            else:
                logger.warning(f"Cache missing: {cache_path} (falling back to network GET)")

        logger.info(f"GET {url}")

        for attempt in range(self.retries_on_403 + 1):
            self._friendly_pause()
            r = self.session.get(url, timeout=(10, 30))
            logger.info(f"Status {r.status_code} for {url}")

            if r.status_code == 403:
                if attempt < self.retries_on_403:
                    sleep_s = self.sleep_on_403_seconds * (attempt + 1)
                    logger.error(
                        f"403 Forbidden. Sleeping {sleep_s:.0f}s then retrying ({attempt+1}/{self.retries_on_403})..."
                    )
                    time.sleep(sleep_s)
                    continue
                logger.error("403 Forbidden. Giving up for this URL.")
                return None

            r.raise_for_status()
            return r.text

        return None

    def _extract_table(self, html: str, preferred_id: str, team_id_hint: str | None = None):
        """
        Try preferred (player) id first; fall back to team id; then scan all tables for a 'player' column.
        Returns: (DataFrame, kind_str)
        """
        soup = BeautifulSoup(html, "lxml")

        html_block = _find_table_html_by_id(soup, preferred_id)
        if html_block:
            df = pd.read_html(html_block)[0]
            df = _clean_header_rows(df)
            df = _flatten_cols(df)
            return df, ("player" if _is_player_table(df) else "unknown")

        if team_id_hint:
            html_block = _find_table_html_by_id(soup, team_id_hint)
            if html_block:
                df = pd.read_html(html_block)[0]
                df = _clean_header_rows(df)
                df = _flatten_cols(df)
                return df, ("team" if not _is_player_table(df) else "player")

        for t in soup.find_all("table"):
            df_try = pd.read_html(str(t))[0]
            df_try = _clean_header_rows(df_try)
            df_try = _flatten_cols(df_try)
            if _is_player_table(df_try):
                return df_try, "player"

        return pd.DataFrame(), "none"

    def fetch_and_save(self, season_label: str):
        season_str = self.cfg["seasons"][season_label]

        id_hints = {
            "standard":   ("stats_standard",   "stats_squads_standard_for"),
            "shooting":   ("stats_shooting",   "stats_squads_shooting"),
            "passing":    ("stats_passing",    "stats_squads_passing"),
            "possession": ("stats_possession", "stats_squads_possession"),
            "defending":  ("stats_defense",    "stats_squads_defense"),
        }

        for spec in self.tables:
            try:
                # cache_key=spec.name maps to files like data/html_cache/standard.html
                html = self._fetch_html(spec.url, cache_key=spec.name)
                if not html:
                    logger.warning(f"{spec.name}: no HTML fetched (blocked/empty). Skipping.")
                    continue

                player_id, team_id = id_hints.get(spec.name, (spec.html_id, None))
                df, kind = self._extract_table(html, player_id, team_id)

                if df.empty:
                    logger.warning(f"{spec.name}: empty dataframe (no table found).")
                else:
                    if kind != "player":
                        logger.warning(f"{spec.name}: captured '{kind}' table (likely team-level). Verify ids.")
                    out = f"{self.raw_dir}/fbref_{spec.name}_{season_str}.csv"
                    logger.info(f"Save → {out} ({len(df)} rows, kind={kind})")
                    df.to_csv(out, index=False)

            except Exception as e:
                logger.exception(f"Error on {spec.name}: {e}")


def run_phase1(cfg_path="src/config.yml"):
    s = FBRefScraper(cfg_path)
    for label in ["live", "benchmark"]:
        logger.info(f"=== Season: {label} ===")
        s.fetch_and_save(label)

if __name__ == "__main__":
    run_phase1()
