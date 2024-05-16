from collections.abc import Callable
import subprocess
import tempfile
import os
from pathlib import Path
from glob import glob
import iterm2
from functools import partial
from utils import focus, get_config
import time
import logging

config = get_config()

def latex_document(latex: str): # could i add path to macros and preamble, does this slow down the process?
    """ return latex template for embeding latex into inkscape """
    return r"""
\documentclass[12pt,border=12pt]{standalone}
\usepackage{amsmath, amssymb}
\newcommand{\R}{\mathbb R}
\begin{document}
    """ + latex + r"""
\end{document}"""


def gather_and_del(filename: str):
    path = Path(filename)
    file_path = str(path.parent / path.stem)
    files = glob(f'{file_path}.*')
    for file in files:
        os.remove(file)


def add_latex(latex_raw:str): # Add ability to add text without compiling latex
    """ Takes in latex code, converts compiled latex to png from which the png is posted to the system clipboard.
    TODO: allow for latex to be added to inkscape without begin compiled
    """
    logger = logging.getLogger(__name__)
    logger.info("Begging latex to png conversion")
    tmpfile = tempfile.NamedTemporaryFile(mode='w+', delete=False)
    tmpfile.write(latex_document(latex_raw))
    tmpfile.close()
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
    logger = logging.getLogger(__name__)
    tmpfile = tempfile.NamedTemporaryFile(mode='w+', suffix=".tex", delete=False)
    tmpfile.write('$$')
    tmpfile.close()
    logger.debug(f"Opening vim instance with buffer {tmpfile.name}")

    promt_user_for_latex(tmpfile.name) # lauches Iterm2 with nvim, runs untill window is closed
    with open(tmpfile.name, 'r') as f:
        latex = f.read().strip()

    logger.debug(f"Removing file: {tmpfile.name}")
    os.remove(tmpfile.name)
    return latex


def write_latex() -> bool:
    """ latex wrote by user => png copied to clipboard
    TODO: This may be the wrong function but remember to put the curso
    """
    latex = open_vim()
    if latex != '$$':
        add_latex(latex)
        return True

    return False

#def start_inkscape():
#    pass

#def start_shortcut_manager(figure_path: str):
#    config['inkscape-config'] = figure_path
#    save_config(config)


def get_num_windows(app):
    return len(app.terminal_windows)


async def _main(connection, filename: str):
    """ From Iterm2 Api. Opens nvim in a new Iterm2 instance and pauses code execution untill the window is closed.
    filename: nvim
    connection: ?
    """
    app = await iterm2.async_get_app(connection)
    window = app.current_window

    if window is not None:
        new_window = await window.async_create(connection, command=f"/bin/bash -l -c 'nvim {filename}'")
        await new_window.async_set_frame(iterm2.Frame(iterm2.Point(500,500), iterm2.Size(600, 100)))
        focus("Iterm")
        # This is a questionable way to keep script running while user writes latex, hack solution for vim.py
        num_windows = 2
        while num_windows > 1:
            time.sleep(0.1)
            app = await iterm2.async_get_app(connection)
            num_windows = get_num_windows(app)
    else:
        print("No current window")

def promt_user_for_latex(file_path: str):
    """ runs _main """
    #file_path = "/Users/joshuataylor/desktop/test.txt"

    if os.path.isfile(file_path):
        main = partial(_main, filename=file_path)
        iterm2.run_until_complete(main)

    else:
        logging.getLogger(__name__).warning(f"Invalid path: {file_path}")
        raise  ValueError("Invalid file Path")


if __name__ == '__main__':
    latex = write_latex()
