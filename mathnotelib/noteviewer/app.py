from re import sub
import re
from flask import Flask, request, send_file, send_from_directory, abort, jsonify
import subprocess
import shutil
import os

from flask.typing import RouteCallable
from ..note import NotesManager, serialize_category
from ..utils import config_dir, config
from pathlib import Path
import tempfile

OUTPUT_PATH = Path(tempfile.gettempdir()) / "rendered.svg"

app = Flask(__name__, static_folder="static")
ROOT_DIR = Path(config['root'])

def typst_to_svg(path: Path) -> int:
    if not path.is_file():
        return 1
    result = subprocess.run(["tinymist", "compile", path, OUTPUT_PATH], cwd=ROOT_DIR)
    try:
        shutil.move(path.with_suffix(".svg"), OUTPUT_PATH)
    except Exception as e:
        return 1
    return result.returncode

def latex_to_svg(path: Path) -> int:
    if not path.is_file():
        return 1
    result_1 = subprocess.run(["latex", "-interaction=nonstopmode", "-output-directory=/tmp", path], cwd=ROOT_DIR)
    if result_1.returncode != 0:
        return 1
    dvi_path = (Path(tempfile.gettempdir()) / path.stem).with_suffix('.dvi')
    result_2 = subprocess.run(["dvisvgm", dvi_path , "-o", OUTPUT_PATH])
    return result_2.returncode

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/render')
def render():
    # TODO: clean this up
    parent_path, file_name, file_type = Path(request.args.get('parentPath', "")), request.args.get("name", ""), request.args.get("type")

    ext = ".tex" if file_type == "LaTeX" else ".typ" # assumes only two file types...
    path = ROOT_DIR / (parent_path / file_name / file_name).with_suffix(ext)

    if file_type == "Typst":
        return_code = typst_to_svg(path)
    elif file_type == "LaTeX":
        return_code = latex_to_svg(path)
    else: return_code = 1

    if return_code == 1:
        return abort(400, "Invalid path")

    return send_file(OUTPUT_PATH, mimetype="image/svg+xml")


@app.route('/tree')
def tree():
    # root_dir should probably be ROOT_DIR only, to include courses + other things. Different parsing?
    root_dir = Path(ROOT_DIR) / "Notes"
    notes = NotesManager(root_dir)
    tree = serialize_category(notes.root_category)
    return jsonify(tree)


