from enum import CONFORM
from pathlib import Path
import json

CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def load_json(path: Path):
    with open(path, "r") as f:
        val = json.load(f)
    return val

def dump_json(path: Path, dic: dict):
    with open(path, "w") as f:
        json.dump(dic, f, indent=6)

def get_config():
    return load_json(CONFIG_PATH)

def save_config(updated_config: dict):
    dump_json(CONFIG_PATH, updated_config)
