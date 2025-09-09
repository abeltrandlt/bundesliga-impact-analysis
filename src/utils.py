import logging, sys, time, pathlib, yaml
from typing import Dict, Any

def ensure_dir(p: str):
    pathlib.Path(p).mkdir(parents=True, exist_ok=True)

def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return yaml.safe_load(f)

def get_logger(name="bundesliga"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s"))
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
    return logger

def polite_pause(seconds: float):
    time.sleep(seconds)
