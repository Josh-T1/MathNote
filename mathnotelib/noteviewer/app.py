from flask import Flask, request, abort, jsonify, Response
import subprocess
import shutil
from ..note import NotesManager, serialize_category
from ..utils import config
from pathlib import Path
import tempfile

OUTPUT_FILE_NAME = "rendered.svg"

app = Flask(__name__, static_folder="static")
ROOT_DIR = Path(config['root'])

def typst_to_svg(path: Path, tmpdir: Path) -> int:
    output_file_path = tmpdir / OUTPUT_FILE_NAME
    if not path.is_file():
        return 1
    result = subprocess.run(["tinymist", "compile", path, tmpdir/ OUTPUT_FILE_NAME],
                            cwd=ROOT_DIR, stdout=subprocess.DEVNULL ,stderr=subprocess.DEVNULL)
    try:
        shutil.move(path.with_suffix(".svg"), output_file_path)
    except Exception as e:
        return 1
    return result.returncode

def latex_to_svg(path: Path, tmpdir: Path) -> int:
    output_file_path = tmpdir / OUTPUT_FILE_NAME
    if not path.is_file():
        return 1
    result_1 = subprocess.run(["pdflatex", "-interaction=nonstopmode", f"-output-directory={tmpdir}", path],
                              cwd=path.parent, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result_1.returncode != 0:
        return 1
    dvi_path = (Path(tempfile.gettempdir()) / f"{path.stem}.dvi").resolve()
    result_2 = subprocess.run(["pdf2svg", dvi_path , output_file_path],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result_2.returncode

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/render')
def render():
    # TODO: clean this up
    parent_path = Path(request.args.get('parentPath', ""))
    file_name = request.args.get("name", "")
    file_type = request.args.get("type")

    ext = ".tex" if file_type == "LaTeX" else ".typ"
    path = (ROOT_DIR / (parent_path / file_name / f"{file_name}{ext}")).resolve()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        if file_type == "Typst":
            return_code = typst_to_svg(path, tmpdir_path)
        elif file_type == "LaTeX":
            return_code = latex_to_svg(path, tmpdir_path)
        else: return_code = 1

        if return_code == 1:
            return abort(400, "Invalid path")
        with open(tmpdir_path / OUTPUT_FILE_NAME, "r", encoding="utf-8") as f:
            svg_content = f.read()
    return Response(svg_content, mimetype="image/svg+xml")


@app.route('/tree')
def tree():
    # root_dir should probably be ROOT_DIR only, to include courses + other things. Different parsing?
    root_dir = ROOT_DIR / "Notes"
    notes = NotesManager(root_dir)
    tree = serialize_category(notes.root_category)
    return jsonify(tree)
