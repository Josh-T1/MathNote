from flask import Flask, request, abort, jsonify, Response
import subprocess
import shutil
from ..note import NotesManager, serialize_category
from ..utils import config
from pathlib import Path
import tempfile

OUTPUT_FILE_NAME = "rendered.svg"
ROOT_DIR = Path(config['root'])

app = Flask(__name__, static_folder="static")

def typst_to_svg(path: Path, tmpdir: Path) -> int:
    """
    Compile typst file to SVG using tinymist

    path: Path of typst file
    tmpdir: Directory where compilation occurs. Typically a temporary directory to ensure intermediate files (e.g., .aux, .log, .svg) are cleaned up after each run.
    """
    print("typst")
    if not path.is_file():
        return 1

    output_file_path = tmpdir / OUTPUT_FILE_NAME

    result = subprocess.run(
            ["tinymist", "compile", path, "--format", "svg"],
            cwd=path.parent,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
            )
    try:
        shutil.move(path.with_suffix(".svg"), output_file_path)
    except Exception as e:
        return 1

    return result.returncode

def latex_to_svg(path: Path, tmpdir: Path) -> int:
    """
    Compile latex to svg

    path: Path of typst file
    tmpdir: Directory where compilation occurs. Typically a temporary directory to ensure intermediate files (e.g., .aux, .log, .svg) are cleaned up after each run.
    """

    if not path.is_file():
        return 1

    output_file_path = tmpdir / OUTPUT_FILE_NAME

    result_1 = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", f"-output-directory={tmpdir}", path],
              cwd=path.parent,
              stdout=subprocess.DEVNULL,
              stderr=subprocess.DEVNULL
              )

    if result_1.returncode != 0:
        return 1

    pdf_path = (tmpdir/path.stem).with_suffix(".pdf")
    result_2 = subprocess.run(
            ["pdf2svg", pdf_path , output_file_path],
              stdout=subprocess.DEVNULL,
              stderr=subprocess.DEVNULL
              )
    return result_2.returncode

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/render')
def render():
    """
    Get args specifying file to compile along with any options. Compile and return svg code

    return: Response containg svg content
    """
    parent_path = Path(request.args.get('parentPath', ""))
    file_name = request.args.get("name", "")
    file_type = request.args.get("type")

    ext = ".tex" if file_type == "LaTeX" else ".typ"
    path = (ROOT_DIR / (parent_path / file_name / f"{file_name}{ext}")).resolve()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        rendered_path = tmpdir_path / OUTPUT_FILE_NAME

        if file_type == "Typst":
            return_code = typst_to_svg(path, tmpdir_path)
        elif file_type == "LaTeX":
            return_code = latex_to_svg(path, tmpdir_path)
        else: return_code = 1

        if return_code == 1:
            return abort(400, "Invalid path")

        with open(rendered_path, "r", encoding="utf-8") as f:
            svg_content = f.read()

    return Response(svg_content, mimetype="image/svg+xml")


@app.route('/tree')
def tree():
    # root_dir should probably be ROOT_DIR only, to include courses + other things. Different parsing?
    root_dir = ROOT_DIR / "Notes"
    notes = NotesManager(root_dir)
    tree = serialize_category(notes.root_category)
    return jsonify(tree)
