import multiprocessing as mp
import subprocess
import sys
from shutil import copy
from utils import get_config
from hotkey import IK_KeyHandler, IK_ShortcutManager, StatusWindow, user_shortcuts
import logging
import os
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

def create_figure(fig_path):
    logger.info(f"Fig path: {fig_path}")
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

    queue = mp.Queue()
    dir = fig_dir.rsplit('.', 1)[0]

    key_handler = IK_KeyHandler
    short = IK_ShortcutManager(config, dir, key_handler, queue=queue)
    short.register_shortcuts(user_shortcuts())
    window = StatusWindow(queue)

    logging.debug("Starting ShortcutManager, Gui threads and opening Inksape")
    short.start()
    open_inkscape(config['inkscape-exec'], path)
    window.start()
    short.join()



if __name__ == '__main__':
    # Shortcut that calls this script is located at ../nvim/ftplugin/tex.vim
    logger.info("test")
    command = sys.argv[1:]
    match command:
        case ['-c', line, fig_dir]:
            name = line.strip()
            print(include_fig(name))
            create_figure(fig_dir + name)

        case [*_]:
            print("Invalid arguments") # make this logging



