import subprocess
import sys
from pathlib import Path
from shutil import copy
sys.path.insert(0, '../')
from hotkey import ShortCutManager
from config import get_config

config = get_config()
i_config = config['inkscape-config']
def open_inkscape(path: str, start_shortcut_manager=False):
    subprocess.Popen(
            [config['inkscape-config']['inkscape'], path]
            )
    if start_shortcut_manager:
        s = ShortCutManager(config, path)
        s.listen()
# How can I ensure that old figure path is not in config

def create_figure(fig_dir: str, name: str):
    # have a fig directory from root give project location
    copy(config['figure-template'], fig_dir + name)
    open_inkscape(fig_dir + name)

def edit_figure(name, dir):
    pass

def svg_to_pdftex(path: str): # should this be seperate
    pdf_path = str(Path(path).parent / Path(path).stem) + ".pdf"
    subprocess.run(
            [i_config['inkscape'], '--export-area-page', '--export-dpi', i_config['export-dpi'],
             '--export-type=pdf', '--export-latex', '--export-filename', pdf_path],
            stdin=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
            )


if __name__ == '__main__':
    path = '/users/joshuataylor/documents/python/myprojects/mathnote/config/t.svg'
    svg_to_pdftex(path)
