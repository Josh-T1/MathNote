"""
[Use]

This is where additional shortcuts can be supplied to be dynamically loaded at run time. This works in the following way (top down):
    1. There must be a variable SHORTCUTS: list[ShortCut] in the module. Each element in the list must be of type ShortCut
    1. ShortCut objects can be constructed as follows

        ShortCut(
                trigger: str,
                callback: FunctionType,
                mode: Modes,
                description: str | None = None,
                name: str | None = None,
                )

    :param trigger: key(s) pattern that trigger shortcut. If the pattern has multiple keys then the trigger should look like 'cmd+c'.
    :param callback: the function that gets called upon ShortCut being triggered.
    :param mode: pattern matching of shortcut trigger will only occur if mode is equal to IK_ShortcutManager.mode. Walmart version of 'modes' in vim
    :param name: shortcut name
    :param description: shortcut description

    1. Callbacks will be passed the instance of IK_ShortcutManager at run time, giving callbacks access to all methods and properties of the instanciated
    IK_ShortcutManager class. Callbacks can not contain blocking behaviour, however a workaround is provided under limitations section.

    def shortcut(self) -> None:
        ...

    1. All modules used in the shortcut callback must be imported in this file even if they are imported in shortcut_manager.py


[Limitations] (MacOS)

- No blocking behavour is permited within the shortcut callback. In the case where you would like to execute a subprocess, wait, and then continue implementing shortcut logic there is the following workaround
(Assuming said subprocess is running another python file). The IK_ShortcutManager class has a property self.shortcut_in_progress: bool which we can use to instruct the IK_ShortcutManager to remain paused
untill the proces is terminated. We do this through the use of filelocks, the subprocess script must be of the following format:

    from config import PIPELINE_FILENAME, LOCK_FILENAME
    if __name__ == '__main__':
        try:
            subprocess logic
        finally:
            lock.acquire()
            with open(PIPELINE_FILENAME, "w") as file:
                file.write("done")

This allows us to 'pause' or suppress keys untill the process is terminated, however we are still in need of a method for implementing additional
logic for this shortcut. ....


* This limitation is a result of blocking behaviour in the shortcut interfering with the callback
_darwin_intercept supplied to keyboard.Listener(...) as a keyword argument. This may not be an issue on other operating systems, and
likley has a more elegant solutions but fuck it

[Limitations] (Other Operating Systems)
- not implemented ... yet
"""

""" ------- [User Imports] ------- """
import subprocess
from pynput import keyboard
from shortcut_manager import IK_ShortcutManager, Modes, ShortCut
from typing import Type
import utils as utils
from functools import partial
""" ----------------------------- """

"""
Example Shortcut
"""

def add_latex(self: Type['IK_ShortcutManager']) -> None:
    """ Launches new Iterm2 instanace from which vim is opened in a tmp file, if latex is written, it is
    compiled and pasted to inkscape """
    def nested_callback(_self, normal_shortcut) -> None:
        normal_shortcut.enable()
        _self.logger.debug(f"Normal enabled {normal_shortcut.enabled}")
    #        with _self.cont.pressed(keyboard.Key.cmd):
    #            _self.cont.tap('v')
        return None



    normal_shortcut = next((obj for obj in self.shortcuts['insert'] if obj.pattern == "esc"), None) # An absolutely horrendous solution. Need to re think how shortcuts are stored.
    if not normal_shortcut: # This shortcuts functionality is dependent on the existance of the toggle normal mode shortcut
        raise UserWarning("Shortcut dependancy 'toggle normal mode' with pattern 'esc' is not found")

    normal_shortcut.disable()
    self.toggle_mode(Modes.Insert)
    subprocess.Popen(["python3", "/Users/joshuataylor/documents/python/myprojects/mathnote/shortcut_manager/latex_utils.py"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    self.callable_queue.append(partial(nested_callback, _self=self, normal_shortcut=normal_shortcut))
    utils.bring_app_to_foreground("Inkscape")


SHORTCUTS = [
        ShortCut("t", add_latex, Modes.Normal, contains_subprocess = True, description="Open instance of vim, to which all tex will be compiled and saved to clipboard")
        ]
