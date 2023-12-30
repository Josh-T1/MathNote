import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"

def get_config():
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    return config

def save_config(updated_config: str):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(updated_config, f, indent=6)

