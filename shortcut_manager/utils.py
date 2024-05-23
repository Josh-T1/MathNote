from logging.config import fileConfig
import subprocess
from pathlib import Path
import json
import logging
import os
from functools import partial
import subprocess
from glob import glob
import tempfile
from types import FunctionType, ModuleType
import importlib
import sys as sys
import asyncio
import iterm2

CONFIG_PATH = Path(__file__).parent.parent / "config.json"

def get_config():
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
    return config

config = get_config()
logging.basicConfig(
        level = logging.DEBUG,
        format='%(asctime)s %(name)s %(levelname)s: %(message)s',
        filename = "utils.log",
        force=True
        )
logger = logging.getLogger(__name__)
logger.debug("CONFIG WORKS")

def save_config(updated_config: str):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(updated_config, f, indent=6)

def include_fig(name: str) -> str:
    """ returns latex code to include figure, where figure is assumed to live in figures folder (/class/figures) """
    return fr"""
\begin{{figure}}[ht]
    \centering
    \incfig{{{name}}}
    \label{{{name}}}
\end{{figure}}
"""

def latex_document(latex: str) -> str: # could i add path to macros and preamble, does this slow down the process?
    """ return latex template for embeding latex into inkscape """
    return r"""
\documentclass[12pt,border=12pt]{standalone}
\usepackage{amsmath, amssymb}
\newcommand{\R}{\mathbb R}
\begin{document}
    """ + latex + r"""
\end{document}"""


def focus(app_name: str):
    """ Bring application 'app_name' to foreground
    :param app_name: str"""
    subprocess.call(
            ["osascript", "-e", f"'tell application \"{app_name}\" to activate'"]
            )
#    subprocess.call(
#            ["osascript", "-e", f'activate application "{app_name}"']
#            )

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
        tmpf.write(latex_document(latex_raw))

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
        logger.debug("finished writing tex") # TODO

async def get_num_windows(app) -> int:
    return len(app.terminal_windows)

async def _main(connection, filename: str) -> None:
    """ From Iterm2 Api. Opens nvim in a new Iterm2 instance and pauses code execution untill the window is closed.
    filename: nvim
    connection: ?
    """
    app = await iterm2.async_get_app(connection)
    window = app.current_window
    if window is None:
        raise Exception("Windown is none")

    num_windows = await get_num_windows(app)
    new_window = await window.async_create(connection, command=f"/bin/bash -l -c 'nvim {filename}'")
    await new_window.async_set_frame(iterm2.Frame(iterm2.Point(500,500), iterm2.Size(600, 100)))
#    focus("Iterm") # there is an error with this

    while await get_num_windows(app) > num_windows:
        await asyncio.sleep(0.1)
    print("done")

def promt_user_for_latex(file_path: str) -> None:
    """ runs _main """
    #file_path = "/Users/joshuataylor/desktop/test.txt"
    if not os.path.isfile(file_path):
        logger.error(f"Invalid path: {file_path}")
        raise  ValueError("Invalid file path: {file_path}")

    main = partial(_main, filename=file_path)
    iterm2.run_until_complete(main)




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


def open_inkscape(exe_path:str, path: str) -> None:
    """
    path: target figure path
    exe_path: path to inkcape executable
    """
    subprocess.Popen([exe_path, path])
