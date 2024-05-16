import subprocess
from contextlib import contextmanager
import sys
import os
from pathlib import Path
import json
import logging

CONFIG_PATH = Path(__file__).parent.parent / "config.json"

def get_config():
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    return config

def save_config(updated_config: str):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(updated_config, f, indent=6)

def focus(app_name):
    subprocess.call(
            ["osascript", "-e", f'activate application "{app_name}"']
            )

def svg_to_pdftex(path: str, ink_exec: str, export_dpi: str):
    """" dst: file destination
    ink_exec: path to inkscape executable
    Issures: (1) names are not required (2) Is it possible we do not specify an input file name?
    """
    #tmp fix
    path = path.split(".")[0]
    logging.getLogger(__name__).info(f"Exporting to {path} to pdf and pdf_tex")
    subprocess.run(
            [ink_exec, path + "svg", '--export-area-page', '--export-dpi', export_dpi,
             '--export-type=pdf', '--export-latex', '--export-filename', path+"pdf"],
            stdin=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
            )

@contextmanager
def silent_stdout():
    old_target = sys.stdout
    try:
        with open(os.devnull, mode='w') as new_target:
            sys.stdout = new_target
            yield new_target
    finally:
        sys.stdout = old_target

