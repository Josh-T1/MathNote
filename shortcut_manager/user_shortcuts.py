import subprocess
from pynput import  keyboard
from utils import focus
from shortcut_manager import IK_ShortcutManager, Modes, ShortCut
from typing import Type


# I need some sort of error handling for invalid tex compilation. What if I made a guid logger
def add_latex(self: Type['IK_ShortcutManager']) -> None:
    """ Launches new Iterm2 instanace from which vim is opened in a tmp file, if latex is written, it is
    compiled and pasted to inkscape """
    normal_shortcut = next((obj for obj in self.shortcuts['insert'] if obj.pattern == "esc"), None) # An absolutely horrendous solution. Need to re think how shortcuts are stored.
    if not normal_shortcut: # This should be unessasary
        return

    normal_shortcut.disable()
    self.logger.debug(f"Normal shortcut: {normal_shortcut.active}")
    subprocess.Popen(["python3", "/Users/joshuataylor/documents/python/myprojects/mathnote/shortcut_manager/latex_utils.py"],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    self.toggle_mode(Modes.Insert)
    focus("Inkscape") # Why the fuck does this not work
    with self.cont.pressed(keyboard.Key.cmd):
        self.cont.tap('v')

SHORTCUTS = [
        ShortCut("t", add_latex, Modes.Normal, description="Open instance of vim, to which all tex will be compiled and saved to clipboard")
        ]
