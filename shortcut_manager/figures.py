from contextlib import redirect_stdout
import multiprocessing as mp
import subprocess
import sys
from shutil import copy
from utils import get_config
from hotkey import IK_KeyHandler, IK_ShortcutManager, StatusWindow, user_shortcuts
import logging
import os
from utils import silent_stdout

config = get_config()

LEVEL = logging.DEBUG

cwd = __file__.rsplit("/", 1)[0]
logging.basicConfig(
        level=LEVEL,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        filename=cwd+"/shortcut_manager.log"
        )
logger = logging.getLogger(__name__)

# This files serves as an interface between vim shortcuts and python code for shortcuts
def include_fig(name):
    """ returns latex code to include figure, where figure is assumed to live in figures folder (/class/figures) """
    return fr"""
\begin{{figure}}[ht]\n
    \centering
    \incfig{{{name}}}
    \label{{{name}}}
\end{{figure}}
"""

def open_inkscape(exe_path:str, path: str):
    """
    path: target figure path
    exe_path: path to inkcape executable
    """
    subprocess.Popen(
            [exe_path, path]
            )
# How can I ensure that old figure path is not in config

def create_figure(fig_path: str):
    logger.info(f"Fig path: {fig_path}")
    # check to see if path already exists
    # have a fig directory from root give project location
    copy(config['figure-template'], fig_path)
    logging.info(f"Creating inkscape figure: {fig_path} and opening inkscape with ShortcutManager")
    open_inkscape_with_manager(fig_path)

def edit_figure(name, dir):
    pass

def open_inkscape_with_manager(path: str):
    """ Instanciates queue pipeline between IK_ShortcutManager and IK_StatusWindow
    config: WHAT CONFIG TIS THIS SOOOORT OUT CONFIG*************
    path: target figure directory
    """
    gui_queue = mp.Queue()
#    dir = path.rsplit('.', 1)[0]
    logger.debug(f"path: {path}")
    key_handler = IK_KeyHandler
    short = IK_ShortcutManager(config, path, key_handler, gui_queue)
#    short.register_shortcuts(user_shortcuts())
#    window = StatusWindow(gui_queue, short)


    logger.debug("Starting threads for ShortcutManager and Gui. Opening Inksape")
    short.start()
    open_inkscape(config['inkscape-exec'], path)
#    window.start() # runs on main thread
    short.join()

def run_test():
    dir = os.getcwd()
    path = dir + "fig.svg"
    open_inkscape_with_manager(path)


def main():
    logger.info("test")
    command = sys.argv[1:]
    match command:
        case ['-c', line, fig_dir]:
            name = line.strip()
            with redirect_stdout(None):
                # This supresses stdout, in particular the warning from tkinter
                create_figure(fig_dir + name + ".svg")

            print(include_fig(name))
        case [*_]:
            print("Invalid arguments") # make this logging

if __name__ == '__main__':
    # Shortcut that calls this script is located at ../nvim/ftplugin/tex.vim
    main()

