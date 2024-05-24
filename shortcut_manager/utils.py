import subprocess
from pathlib import Path
import json
import logging
import os
import subprocess
from glob import glob
import tempfile
from types import FunctionType
import importlib
import sys as sys
import config as config
import platform

"""
OS specific Imports
"""
if platform.system() == "Darwin":
    import macos_specific as os_specific
else:
    raise OSError(f"Unsupported operating system: {platform.system()}")


CONFIG_PATH = Path(__file__).parent.parent / "config.json"
logger = logging.getLogger("ShortCutManager")


def is_app_running(app_name):
    os_specific.is_app_running(app_name)

def bring_app_to_foreground(app_name):
    os_specific.bring_app_to_foreground(app_name)

def close(app_name):
    os_specific.close_app(app_name)

def get_config():
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    return config

def promt_user_for_latex(file_path: str) -> None:
    os_specific.promt_user_for_latex(file_path)


def save_config(updated_config: str):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(updated_config, f, indent=6)

def svg_to_pdftex(path: str, ink_exec: str, export_dpi: str):
    """"
    :param dst: file destination
    :param ink_exec: path to inkscape executable
    """
    # tmp fix
    path = path.split(".")[0]
    logging.getLogger(__name__).info(f"Exporting to {path} to pdf and pdf_tex")
    subprocess.run(
            [ink_exec, path + "svg", '--export-area-page', '--export-dpi', export_dpi,
             '--export-type=pdf', '--export-latex', '--export-filename', path+"pdf"],
            stdin=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
            )

def gather_and_del(filename: str):
    """ Delete all files in a directory by name ignoring extension """
    path = Path(filename)
    file_path = str(path.parent / path.stem)
    files = glob(f'{file_path}.*')
    for file in files:
        os.remove(file)


def add_latex(latex_raw: str): # Add ability to add text without compiling latex
    """ Takes in latex code, converts compiled latex to png from which the png is posted to the system clipboard.
    TODO: allow for latex to be added to inkscape without begin compiled
    """
    logger.debug("Starting latex to png conversion")
    tmpfile = tempfile.NamedTemporaryFile(mode='w+', delete=False)

    with open(tmpfile.name, "w") as tmpf:
        tmpf.write(config.latex_document(latex_raw))

    working_dir = tempfile.gettempdir()
    subprocess.run(
            ['pdflatex', tmpfile.name],
            cwd=working_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
            )
    subprocess.run(
            [config["inkscape-exec"],f'{tmpfile.name}.pdf', "--export-type=png", f'--export-dpi={config["export-dpi"]}', f'--export-filename={tmpfile.name}.png'],
            cwd=working_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
            )
    logger.info(f"Copying png: {tmpfile.name}.png to clipboard")
    subprocess.run(
            ["osascript", "-e", f'set the clipboard to (read (POSIX file "{tmpfile.name}.png") as  {{«class PNGf»}})'],
            )

    if not os.path.exists(config['.data']):
        Path(config['.data']).touch()

    with open(config['.data'], mode='w') as f:
        pattern = f"{str(tmpfile.name)}.*"
        files = glob(pattern)
        f.write('\n'.join(files))

def open_vim() -> str: # send 'a'
    """  Opens vim with tmpfile as buffer to which latex code is wrote by user.
    TODO: Send a to buffer to automate inizializing of write to buffer
    """
    tmpfile = tempfile.NamedTemporaryFile(mode='w+', suffix=".tex", delete=False)
    with open(tmpfile.name, 'w') as tmpf:
        tmpf.write('$$')

    logger.debug(f"Opening vim instance with buffer {tmpfile.name}")
    promt_user_for_latex(tmpfile.name) # lauches Iterm2 with nvim, runs untill window is closed

    with open(tmpfile.name, 'r') as f:
        latex = f.read().strip()

    logger.debug(f"Removing file: {tmpfile.name}")
    os.remove(tmpfile.name)
    return latex


def write_latex() -> None:
    """ latex wrote by user => png copied to clipboard
    TODO: This may be the wrong function but remember to put the curso
    """
    logger.debug("starting to write tex")
    latex = open_vim()
    if latex != '$$':
        add_latex(latex)

def load_shortcuts(module_path: str) -> list[FunctionType]:
    """ Loads modules from path set in config file. Then finds all functions in the module that start with
    shortcut_prefix
    :param module_path: path to module
    """
    shortcuts = []
    shortcuts_name = "SHORTCUTS"

    # Add module dir to path
    module_dir = os.path.dirname(module_path)
    sys.path.insert(0, module_dir)
    module_name = os.path.splitext(os.path.basename(module_path))[0]

    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        logger.error(f"Failed to load module with name: {module_name}, path: {module_path}, error: {e}")
        return shortcuts

    for name, obj in module.__dict__.items():
        if not isinstance(obj, list):
            continue
        if name == shortcuts_name:
            return obj
    return shortcuts


def launch_inkscape_with_figure(figure_path: str):
    subprocess.Popen(["open", "-a", INKSCAPE_PATH, figure_path])

