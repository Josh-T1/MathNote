import subprocess
from pathlib import Path
import json
import logging
import os
import subprocess
from glob import glob
import tempfile
from types import FunctionType
import importlib.util
import sys
import config as config_
import platform



""" Config """ # relocated to ../global_utils.py ... hopefully I found all instances in the module
#CONFIG_PATH = Path(__file__).parent.parent / "config.json"
#logger = logging.getLogger("ShortCutManager")
#
#def get_config():
#    with open(CONFIG_PATH, 'r') as f:
#        config = json.load(f)
#    return config
#config = get_config()

""" os specific Imports """
if platform.system() == "Darwin":
    import macos_specific as os_specific
else:
    raise OSError(f"Unsupported operating system: {platform.system()}")
INKSCAPE_PATH = os_specific.INKSCAPE_PATH

def set_png_to_clipboard(png_path):
    os_specific.set_png_to_clipboard(png_path)

def is_app_running(app_name):
    os_specific.is_app_running(app_name)

def bring_app_to_foreground(app_name):
    os_specific.bring_app_to_foreground(app_name)

def close(app_name):
    os_specific.close_app(app_name)



def promt_user_for_latex(file_path: str) -> None:
    os_specific.promt_user_for_latex(file_path)
""" ======================================== """


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

def add_latex():
    """
    Idealy one would write latex, embed it into svg and past the svg from clipboard into inkscape...however mac clipboard does not support svg
    """
    raise NotImplemented
#    latex = open_vim()
#    subprocess.run(
#            ["pbcopy"], text = True, input = latex
#            )

def add_compiled_latex(): # Add ability to add text without compiling latex
    """TODO: WIRTEO LKSJfl Takes in latex code, converts compiled latex to png from which the png is posted to the system clipboard.
    TODO: allow for latex to be added to inkscape without begin compiled
    """
    latex = open_vim()

    if latex == '$$':
        return

    logger.debug("Starting latex to png conversion")
    tmpfile = tempfile.NamedTemporaryFile(mode='w+', delete=False)

    with open(tmpfile.name, "w") as tmpf:
        tmpf.write(config_.latex_document(latex))

    working_dir = tempfile.gettempdir()
    # latex code -> pdf
    subprocess.run(
            ['pdflatex', tmpfile.name],
            cwd=working_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
            )
    # pdf -> png
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


# https://stackoverflow.com/a/67692 -> better solutions?

def launch_inkscape_with_figure(figure_path: str):
    subprocess.Popen(["open", "-a", INKSCAPE_PATH, figure_path])

def lazy_import(name):
    spec = importlib.util.find_spec(name)
    if not spec or not spec.loader:
        return None
    loader = importlib.util.LazyLoader(spec.loader)
    spec.loader = loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module

def load_shortcuts(module) -> list[ShortCut]:
    """ Loads modules from path set in config file. Then finds all functions in the module that start with
    shortcut_prefix
    :param module: module object
    """
    shortcuts_name = "SHORTCUTS"

    for name, obj in module.__dict__.items():
        if not isinstance(obj, list):
            continue
        if name == shortcuts_name:
            return obj
    return []
