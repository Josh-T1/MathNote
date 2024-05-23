import importlib
import subprocess
import sys
from shutil import copy
from types import ModuleType, FunctionType
import utils as utils
from shortcut_manager import IK_ShortcutManager, StatusWindow
import logging
import os
import logging.config

config = utils.get_config()

logging.config.dictConfig(config = config["shortcutmanager-logging-config"])
logger = logging.getLogger("ShortCutManager")


# How can I ensure that old figure path is not in config

def create_figure(fig_path: str) -> None:
    logger.info(f"Fig path: {fig_path}")
    # check to see if path already exists
    # have a fig directory from root give project location
    copy(config['figure-template'], fig_path)
    logging.info(f"Creating inkscape figure: {fig_path} and opening inkscape with ShortcutManager")
    open_inkscape_with_manager(fig_path)

def edit_figure(name, dir):
    raise NotImplemented

def open_inkscape_with_manager(path: str):
    """ Instanciates queue pipeline between IK_ShortcutManager and IK_StatusWindow
    path: save location for figure
    """
    shortcut_manager = IK_ShortcutManager(config, path)
    window = StatusWindow()

    shortcuts_obj = utils.load_shortcuts(config["user-shortcuts-path"])

    shortcut_manager.register_shortcuts(shortcuts_obj)
    shortcut_manager.add_obsever(window)
    logger.debug("Starting threads for ShortcutManager and Gui. Opening Inksape")
    shortcut_manager.start()
    utils.open_inkscape(config['inkscape-exec'], path)
    window.inizialize()
    shortcut_manager.join()

def test_shortcuts():
    all_tests_passed = True


def main():
    # Should I be using .svg to create figure or
    command = sys.argv[1:]
    logger.debug(f"System args: {sys.argv}")
    match command:
        case ['-c', line, fig_dir]:
            name = line.strip()
            if not name:
                raise ValueError("No figure name specified")
            create_figure(fig_dir + name + ".svg")
            tex = utils.include_fig(name)
            print(tex)

        case [*_]:
            logger.error("Invalid arguments")


def disassemble_bytecode(func: FunctionType) -> str:
    """Disassembles the bytecode of a function and returns it as a string."""
    import dis
    bytecode_instructions = dis.Bytecode(func)
    return ''.join([instruction.opname + '\n' for instruction in bytecode_instructions])




if __name__ == '__main__':
    # Shortcut that calls this script is located at ../nvim/ftplugin/tex.vim
    main()
