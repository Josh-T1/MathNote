import os
import logging
import multiprocessing as mp
from pynput import keyboard
from enum import Enum
from utils import svg_to_pdftex
from typing import Callable, Union, Optional
import tkinter as tk
import time
import threading
from functools import partial
from utils import focus
from vim import write_latex

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)

class Modes(Enum):
    Normal = "normal"
    Insert = "insert"
    Close = "close"

class IK_ShortcutManager():
    def __init__(self, config: dict, figure_path: str, key_handler, queue: Optional[mp.Queue] = None):
        """ Shortcuts can not contain esc character or 'i'.
        config: config dictionary
        figure_path: is the desired save location for inkscape figure
        """
        self.logger = logging.getLogger(__name__ + "ShortcutManager")
        self.shortcuts = {"normal": {}, "insert": {}}
        self.queue = queue
        self.key_handler = key_handler(self.shortcuts)
        self._set_sane_defaults()


        self.config = config
        self.figure_path = figure_path
        self.cont = keyboard.Controller()
        self.mode = Modes.Insert
        self.toggle_mode(Modes.Insert) #hack solution to update gui

        self.listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release, darwin_intercept=self._darwin_intercept)

    def _set_sane_defaults(self):
        self.register_shortcuts([
                ("cmd+c", self.close, "normal", True),
                ("esc", partial(self.toggle_mode, mode=Modes.Normal), "insert", True),
                ('i', partial(self.toggle_mode, mode=Modes.Insert), "normal", True),
                ])

    def start(self):
        """ Start keyboard.Listener() thread """
        self.logger.info("Listener thread is starting")
        self.listener.start()

    def join(self):
        """ impliments threading.Thread().join() method and handles key interrupt """
        try:
            self.listener.join()
        except KeyboardInterrupt:
            self.logger.warning("Shortcut Manager was stopped with a KeyboardInterrupt")
            self.close()

    def close(self):
        """ The shortcut mangers is closed when the keyboard listener is terminated. This occurs when there is keyboard interupt or when the
        close shortcut is called.
        """
        self.logger.info("Starting ShortcutManager close")
        self._delete_tmp_files()
        self.save_fig()
        self.toggle_mode(Modes.Close) # this closes listener

    def _delete_tmp_files(self):
        """ Delete all files created as a result of compiling latex code: latex => pdf => png => clipboard """
        with open(self.config['.data'], mode='r+') as f:
            files  = f.read().split('\n')
            f.truncate(0)
            f.seek(0)
        for file in files:
            if file != '':
                self.logger.debug(f"Deleting tmp file: {file}")
                os.remove(file)

    def toggle_mode(self, mode: Modes) -> None:
        self.mode = mode
        if self.queue != None:
            self.queue.put(mode.value)

    def _darwin_intercept(self, event_type, event):
        """ Allows for keys to be intercepted and blocked from being sent to stdout by Listener if mode=normal """
        if self.mode == Modes.Normal:
            return None
        else:
            return event

    def _on_press(self, key) -> None:
        self.key_handler.pressed_key(key)

    def _on_release(self, key: keyboard.Key) -> Union[bool, None]: # make sure closing the __enter__ condition trigers __exit__
        """ Check for pattern activation on key release and call corresponding shorcut handler if active. If mode is closing,
        thread.Listener() object is terminated on release
        """
        res = self.key_handler.handle(self.mode.value, key)
        if callable(res):
            res()

        if self.mode == Modes.Close:
            return False

    def register_shortcut(self, shortcut: str, handler: Callable, mode: str, method=False):
        """ Adds shortcut
        method: True if shortcut handler is IK_ShortcutManager method
        """
        if mode not in self.shortcuts.keys():
            self.logger.warning(f"Mode: {mode} is not supported")
            return
        if not method:
            handler = partial(handler, inst=self)
        self.shortcuts[mode][shortcut] = handler
        self.key_handler.register_shortcut(shortcut, handler, mode)

    def register_shortcuts(self, shortcuts: list[tuple]):
        """ Shortcuts: [(shortcut: str, handler: Callable, mode:str),...] """
        for shortcut in shortcuts:
            self.register_shortcut(*shortcut)

    def save_fig(self) -> None:
        """ Saves figure and makes pdf and pdf_tex copies of the figure """
        self.logger.info(f"Saving figure: {self.figure_path}")
        self.toggle_mode(Modes.Insert)
        with self.cont.pressed(keyboard.Key.cmd):
            self.cont.tap('s')

        #dst = self.figure_path.rsplit('.')[0] + ".pdf"
        svg_to_pdftex(self.figure_path, self.config['inkscape-exec'], self.config['export-dpi'])




class IK_KeyHandler():
    """ Responsible for handling keys and matching key patterns """
    def __init__(self, shortcuts: dict[str, dict]):
        self.logger = logging.getLogger(__name__ + "KeyHandler")
        self.shortcuts = shortcuts
        self.pressed = []

    def pressed_key(self, key):
        self.pressed.append(self.key_to_str(key))

    def register_shortcut(self, pattern: str, func: Callable, mode: str = "insert") -> None:
        self.shortcuts[mode][pattern] = func


    def handle(self, mode: str, key: keyboard.Key) -> Union[None, Callable]:
        """ Dynamically handles on_release behaviour """
        patterns_mode = self.shortcuts[mode]
        pattern = '+'.join(self.pressed)

        if pattern in patterns_mode.keys():
            self.logger.debug(f"Calling shortcut handler for shotcut: {pattern}")
            self.pressed.clear()
            return patterns_mode[pattern]

        for key_ in self.shortcuts.keys(): # find patterns when keys are pressed to fast
            if pattern in key_ and pattern != '':
                self.logger.debug(f"Partial match with '{pattern}'")
                return None

        self.logger.debug(f"No pattern was found, clearing pressed. Pressed: {self.pressed}, Pattern: {pattern}")
        self.pressed.clear()
        return None

    @staticmethod
    def key_to_str(key: keyboard.Key) -> str:
        """
        Simplifies Key__repr__() to a more readable format. ex: "'Key.cmd: key_code'" -> 'cmd'
        """
        return key.__repr__().replace("'", '').split('.')[-1].split(':')[0]

class StatusWindow:
    """ MacOS sonoma => warning message displayed when pygui window is created . suppress for in tex.vim
    - try updating python?
    - should I and can I suppress warning?
    """
    def __init__(self, queue: mp.Queue, height=30, width=150) -> None:
        self.root = tk.Tk()
        self.root.geometry(f"{width}x{height}+{self.root.winfo_screenheight()}+{0}")
        self.status_label = tk.Label(self.root, text="waiting")
        self.status_label.pack()
        self.queue = queue

    def retreive_mode(self):
        try:
            mode = self.queue.get()
            return mode
        except mp.Queue.empty:
            return None

    def close(self):
        # is there a reason quit() not destroy()
        self.root.quit()

    def start(self):
        """ inizialize gui mainloop then start gui logic thread """
        thread = threading.Thread(target=self.after)
        self.root.after(1000,thread.start)
        self.root.mainloop()

    def after(self):
        """ Logic loop for updating gui mode label. Called after mainloop() is started """
        current_state = None
        while True:
            res = self.retreive_mode()

            if res != None and res != current_state:
                self.change_mode(res)

                if res == "close":
                    self.root.quit()
                    break

                current_state = res

            time.sleep(1)

    def change_mode(self, mode):
        self.status_label.config(text=mode)

# =================================================================
# Shortcut Functions
def add_latex(inst) -> None:
    """ Launches new Iterm2 instanace from which vim is opened in a tmp file, if latex is written, it is
    compiled and pasted to inkscape
    inst: IK_KeyHandler instance
    """
    wrote = write_latex()
    focus("Inkscape")
    inst.toggle_mode(Modes.Insert)
    if wrote:
        with inst.cont.pressed(keyboard.Key.cmd):
            inst.cont.tap('v')


def user_shortcuts():
    """ returns user shortcuts in form of list of tuples """
    return [
            ('t', add_latex, "normal")
            ]


