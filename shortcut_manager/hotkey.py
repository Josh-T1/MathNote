from multiprocessing import queues
import os
import logging
import queue as queue
import multiprocessing as mp
import subprocess
from pynput import keyboard
from enum import Enum
from typing import Callable, Union, Optional
import tkinter as tk
import time
import threading
from functools import partial
from utils import focus, svg_to_pdftex
from vim import write_latex

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)

class Modes(Enum):
    Normal = "normal"
    Insert = "insert"
    Close = "close"
    Pause = "pause"

class ShortCut():
    def __init__(self,
                 pattern: str,
                 callback: Callable,
                 mode: Modes,
                 builtin: bool = False,
                 name = None,
                 description = None
                 ) -> None:
        self.name = name if name != None else pattern
        self.description = description if description != None else pattern
        self.pattern = pattern
        self.callback = callback
        self.mode = mode
        self.builtin = builtin
        self.active = True

    def activate(self) -> None:
        self.active = True

    def disable(self) -> None:
        self.active = False

    def __repr__(self) -> str:
        return f"{self.__class__} with {{Name: {self.name}, Pattern: {self.pattern}}}"

class IK_ShortcutManager():
    def __init__(self, config: dict, figure_path: str):
        """ Shortcuts can not contain esc character or 'i'.
        config: config dictionary
        figure_path: is the desired save location for inkscape figure
        subprocess_queue: subprocess's are put into subprocess_queue where they are executed in another thread
        """
        self.logger = logging.getLogger(__name__ + "ShortcutManager")
        self.shortcuts = {"normal": [], "insert": []}
        self.pressed = []
        self._set_sane_defaults()
        self.observers = []
        self.config = config
        self.figure_path = figure_path
        self.cont = keyboard.Controller()
        self.mode = Modes.Insert

        self.toggle_mode(Modes.Insert) #hack solution to update gui

    def _set_sane_defaults(self):
        self.register_shortcuts([
                (ShortCut("cmd+c", self.close, "normal", builtin=True, name="Close")),
                (ShortCut("esc", partial(self.toggle_mode, mode=Modes.Normal), "insert", builtin=True, name = "NormalMode")),
                (ShortCut("tab", self.activate_all, "insert", builtin=True, name = "Unpause")),
                (ShortCut("i", partial(self.toggle_mode, mode=Modes.Insert), "normal", builtin=True, name = "InsertMode")),
                (ShortCut("t", self.add_latex, "normal", builtin=True, name = "Term")),
                ])

    def start(self):
        """ Creates keyboard.Listener() and starts thread """
        self.listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release, darwin_intercept=self._darwin_intercept)
        self.logger.info("Listener thread is starting")
        self.listener.start()

    def activate_all(self):
        """ Activate all shortcuts and puts user into normal mode. This is a bad attempt at fixing the issue of esc key interference with the latex shortcut"""
        for _, v in self.shortcuts.items():
            for shortcut in v:
                shortcut.activate()
        self.toggle_mode(Modes.Normal)

    def join(self):
        """ impliments threading.Thread().join() """
        try:
            self.listener.join()
        except KeyboardInterrupt:
            self.logger.warning("Shortcut Manager was stopped with a KeyboardInterrupt")
            self.close() # THis does not work as self.close asumeses thread is running

    def close(self):
        self.logger.info("Starting ShortcutManager close")
        self._delete_tmp_files()
        self.save_fig()
        self.toggle_mode(Modes.Close)
        self.listener.stop()


    def _delete_tmp_files(self):
        """ Delete all tmp files resulting from compilation of latex code. Clean up of the process: .tex => .pdf => .png => clipboard """
        with open(self.config['.data'], mode='r+') as f:
            files  = f.read().split('\n')
            f.truncate(0)
            f.seek(0)
        for file in files:
            if file != '':
                self.logger.debug(f"Deleting tmp file: {file}")
                os.remove(file)

    def toggle_mode(self, mode: Modes) -> None:
        """ Change object mode state and notify gui window through the queue """
        self.mode = mode
        self.notify_observers()

    def _darwin_intercept(self, event_type, event):
        """ Allows for keys to be intercepted and blocked from being sent to stdout if mode=normal. Darwing_intercept is MacOS specific """
        if self.mode == Modes.Normal:
            return None
        else:
            return event

    def _on_press(self, key) -> None:
        self.pressed.append(self.key_to_str(key))

    def _on_release(self, key: keyboard.Key) -> Union[bool, None]: # make sure closing the __enter__ condition trigers __exit__
        """ Returning False stops keyboard.Listener() """
        val = self.handle(self.mode, key)
        if callable(val):
            val()
            self.logger.debug("Succesfully called shortcut callback")

        if self.mode == Modes.Close:
            self.logger.info("Closing keyboard.Listener() thread")
            return False

    def register_shortcut(self, shortcut: ShortCut):
        """ If shortcut has callback function that has not yet been passed class instance, class instance is passed.
        Shortcuts are appended to lists corresponding to their mode.
        shortcut: ShorctCut object """
        if shortcut.mode not in self.shortcuts:
            raise NotImplemented
        if not shortcut.builtin:
            setattr(self, shortcut.callback.__name__, shortcut.callback)
        self.shortcuts[shortcut.mode].append(shortcut)

    def register_shortcuts(self, shortcuts: list[ShortCut]):
        for shortcut in shortcuts:
            self.register_shortcut(shortcut)

    def save_fig(self) -> None:
        """ Saves Inkscape figure and converts to pdftex """
        self.logger.info(f"Saving figure: {self.figure_path}")
        self.toggle_mode(Modes.Insert)
        with self.cont.pressed(keyboard.Key.cmd):
            self.cont.tap('s')

        svg_to_pdftex(self.figure_path, self.config['inkscape-exec'], self.config['export-dpi'])

    def handle(self, mode: Modes, key: keyboard.Key) -> Union[None, Callable]:
        """ Rename this also there is an issue with matching as user needs to press 'ii' to triger shortcut with triger 'i' """
        # Instant reject conditions
        if len(self.pressed) == 0 or mode == Modes.Pause:
            self.pressed.clear()
            return None

        shortcuts_target_mode = self.shortcuts[mode.value]
        pattern = '+'.join(self.pressed)

        for shortcut in shortcuts_target_mode:
            if not shortcut.active: # Some shortcuts may 'disable' others. ie) latex shortcut pauses 'esc' shortcut so that writing to file in vim is possible
                continue

            key_ = shortcut.pattern
            # Case: full match
            if pattern == key_:
                self.logger.debug(f"Calling shortcut callback, Pattern = {pattern}")
                self.pressed.clear()
                return shortcut.callback

            # Case: partial match
            if pattern in key_ and pattern != '':
                self.logger.debug(f"Partial match with '{pattern}'")
                return None

        # Case: no match
        self.logger.debug(f"No pattern was found, clearing pressed. Pressed: {self.pressed}, Pattern: {pattern}")
        self.pressed.clear()
        return None

    def add_obsever(self, observer):
        self.observers.append(observer)

    def notify_observers(self):
        for observer in self.observers:
            observer.update(self.mode.value)


    @staticmethod
    def key_to_str(key: keyboard.Key) -> str:
        """ Simplifies Key__repr__() to a more readable format. ex: "'Key.cmd: key_code'" -> 'cmd' """
        return key.__repr__().replace("'", '').split('.')[-1].split(':')[0]


    def add_latex(self) -> None:
        """ Launches new Iterm2 instanace from which vim is opened in a tmp file, if latex is written, it is
        compiled and pasted to inkscape """
        normal_shortcut = next((obj for obj in self.shortcuts['insert'] if obj.pattern == "esc"), None) # An absolutely horrendous solution. Need to re think how shortcuts are stored.
        if not normal_shortcut: # This should be unessasary
            return

        normal_shortcut.disable()
        self.logger.debug(f"Normal shortcut: {normal_shortcut.active}")
        subprocess.Popen(["python3", "/Users/joshuataylor/documents/python/myprojects/mathnote/shortcut_manager/vim.py"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.toggle_mode(Modes.Insert)
        focus("Inkscape") # Why the fuck does this not work
        with self.cont.pressed(keyboard.Key.cmd):
            self.cont.tap('v')




class StatusWindow:
    """ MacOS sonoma => warning message displayed when pygui window is created
    - Currently supressing warning
    """
    def __init__(self, height: int = 30, width: int = 150) -> None:
        self.root = tk.Tk()
        self.root.geometry(f"{width}x{height}+{self.root.winfo_screenheight()}+{0}")
        self.status_label = tk.Label(self.root, text="waiting")
        self.status_label.pack()
        self.queue = queue.Queue()
        self.logger = logging.getLogger(__name__ + "StatusWindow")
        self.current_state = None
        self.runnig = True

    def retreive_mode(self):
        try:
            mode = self.queue.get_nowait()
            return mode
        except queue.Empty:
            return None

    def update(self, state):
        self.queue.put(state)

    def close(self):
        # is there a reason quit() not destroy()
        self.runnig = False
        self.logger.info("Closing gui window")
        self.root.destroy()
        self.root.quit()


    def inizialize(self):
        """ inizialize gui mainloop then start gui logic thread """
        thread = threading.Thread(target=self.after)
        self.root.after(1000,thread.start)
        self.root.mainloop()

    def after(self):
        """ Logic loop for updating gui mode label. Called after mainloop() is started """
        if self.runnig:
            res = self.retreive_mode()
            if res != None and res != self.current_state:
                self.current_state = res
                self.change_mode(self.current_state)
                self.logger.debug(f"Gui received message: '{res}'")

            if self.current_state == "close":
                self.close()

            else:
                self.root.after(1000, self.after)


    def change_mode(self, mode: str):
        self.status_label.config(text=mode)

# =================================================================
# Shortcut Functions
#def add_latex(inst) -> None:
#    """ Launches new Iterm2 instanace from which vim is opened in a tmp file, if latex is written, it is
#    compiled and pasted to inkscape
#    inst: IK_KeyHandler instance
#    """
#    path = __file__.rsplit('/', 1)[0] + "/vim.py" # assumes these live in same directory
#    output = write_latex()
#    output = wrote.stdout.strip()
#    focus("Inkscape")
#
#    inst.toggle_mode(Modes.Insert)
#    if output == "True":
#
#        with inst.cont.pressed(keyboard.Key.cmd):
#            inst.cont.tap('v')
#
#
#def user_shortcuts():
#    """ returns user shortcuts in form of list of tuples """
#    return [
#            ('t', add_latex, "normal", False)
#            ]
#def queue_retreive(queue):
#    try:
#        res = queue.get()
#        return res
#    except mp.Queue.empty:
#        return None
