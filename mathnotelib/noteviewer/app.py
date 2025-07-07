from flask import Flask, request, send_file, send_from_directory, abort, jsonify
import subprocess
import shutil
import os
from ..note import NotesManager, serialize_category
from ..utils import config_dir, config
from pathlib import Path

OUTPUT_PATH = "/tmp/rendered.svg"

app = Flask(__name__, static_folder="static")

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/render')
def render():
    path = request.args.get('path')
    if path is not None:
        path = "/Users/joshuataylor/MathNote/" + path

    if not path or not os.path.isfile(path) or not path.endswith(".typ"):
        return abort(400, "Invalid path")

    result = subprocess.run(["tinymist", "compile", path, OUTPUT_PATH], cwd="/Users/joshuataylor/MathNote")
    if result.returncode != 0:
        return abort(400, "Invalid path")

    shutil.move(path.replace(".typ", ".svg"), "/tmp/rendered.svg")
    return send_file(OUTPUT_PATH, mimetype="image/svg+xml")


@app.route('/tree')
def tree():
    root_dir = Path(config["root"]) / "Notes"
    notes = NotesManager(root_dir)
    tree = serialize_category(notes.root_category)
    return jsonify(tree)


