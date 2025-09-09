from pathlib import Path
import yaml

from src.scraping import run_phase1

if __name__ == "__main__":
    # just call with the default config path inside scraping.py
    run_phase1()