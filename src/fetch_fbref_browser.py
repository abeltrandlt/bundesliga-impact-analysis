from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

URLS = {
    "standard":   "https://fbref.com/en/comps/20/stats/Bundesliga-Stats",
    "shooting":   "https://fbref.com/en/comps/20/shooting/Bundesliga-Stats",
    "passing":    "https://fbref.com/en/comps/20/passing/Bundesliga-Stats",
    "possession": "https://fbref.com/en/comps/20/possession/Bundesliga-Stats",
    "defending":  "https://fbref.com/en/comps/20/defense/Bundesliga-Stats",
}

# What we expect to exist on each page when it is a real FBref stats page
EXPECTED_TABLE_IDS = {
    "standard": "stats_standard",
    "shooting": "stats_shooting",
    "passing": "stats_passing",
    "possession": "stats_possession",
    "defending": "stats_defense",
}

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

def fetch_pages(out_dir="data/html_cache", headful=True):
    """
    Fetch FBref pages using a real browser context.
    - headful=True opens a visible browser (most reliable vs Cloudflare)
    - Saves HTML only if the expected table id is present
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headful)
        context = browser.new_context(user_agent=UA)
        page = context.new_page()

        for name, url in URLS.items():
            print("GET", url)
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            expected_id = EXPECTED_TABLE_IDS[name]

            # Wait for either the table itself OR the wrapper div to appear
            # (FBref sometimes places tables in commented blocks inside a wrapper)
            try:
                page.wait_for_selector(f"table#{expected_id}, div#all_{expected_id}", timeout=60000)
            except PWTimeout:
                # dump diagnostic html if challenge page
                html = page.content()
                diag_path = out / f"{name}__DIAG.html"
                diag_path.write_text(html, encoding="utf-8")
                print(f"[ERROR] Did not find expected selector for {name}. Saved diagnostic: {diag_path}")
                raise RuntimeError(
                    f"FBref content not loaded for '{name}'. "
                    f"Expected table id '{expected_id}'. Likely Cloudflare challenge."
                )

            # Give FBref a moment to fully populate DOM/comments
            page.wait_for_timeout(2000)

            html = page.content()

            # Validate the HTML really contains the expected id string
            if expected_id not in html:
                diag_path = out / f"{name}__DIAG.html"
                diag_path.write_text(html, encoding="utf-8")
                print(f"[ERROR] Expected id '{expected_id}' not in HTML. Saved diagnostic: {diag_path}")
                raise RuntimeError(
                    f"Fetched HTML for '{name}' does not contain '{expected_id}'. "
                    f"Likely still a challenge/interstitial."
                )

            path = out / f"{name}.html"
            path.write_text(html, encoding="utf-8")
            print("Saved:", path)

        browser.close()

if __name__ == "__main__":
    fetch_pages(headful=True)
