import os
import logging
import queue as queue
from pynput import keyboard
from enum import Enum
from typing import Callable
import tkinter as tk
import threading
from functools import partial
from utils import svg_to_pdftex
from dataclasses import dataclass

logger = logging.getLogger("ShortCutManager")
logger.setLevel(level=logging.DEBUG)

class Modes(Enum):
    Normal = "normal"
    Insert = "insert"
    Close = "close"
    Pause = "pause"

@dataclass
class ShortCut:
    def __init__(self,
                 pattern: str,
                 callback: Callable,
                 mode: Modes,
                 builtin: bool = False,
                 name: str | None = None,
                 description: str | None = None
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

class IK_ShortcutManager:
    def __init__(self, config: dict, figure_path: str):
        """ Shortcuts can not contain esc character or 'i'.
        config: config dictionary
        figure_path: is the desired save location for inkscape figure
        subprocess_queue: subprocess's are put into subprocess_queue where they are executed in another thread
        """
        self.logger = logging.getLogger(__name__ + "ShortcutManager")
        self.shortcuts: dict[str, list] = {"normal": [], "insert": []}
        self.pressed: list = []
        self.observers: list = []
        self.config: dict = config
        self.figure_path: str = figure_path
        self.cont: keyboard.Controller = keyboard.Controller()
        self.mode = Modes.Insert
        self._set_sane_defaults()

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
        """ Implements threading.Thread().join() """
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
        """ Allows for keys to be intercepted and blocked from being sent to stdout if mode=normal. Darwing_intercept is MacOS specific
        :param event: ??? passed by keyboard.Listener
        :param event_type: ??? passed by keyboard.Listener
        """
        if self.mode == Modes.Normal:
            return None
        else:
            return event

    def _on_press(self, key: keyboard.Key) -> None:
        """ Callback for action key pressed
        :param key: passed by keyboard.Listener
        """
        self.pressed.append(self.key_to_str(key))

    def _on_release(self, key: keyboard.Key) -> bool | None: # make sure closing the __enter__ condition trigers __exit__
        """ Callback for action key release
        :param key: passed by keyboard.Listener
        Note: returning False stops keyboard.Listener()
        """
        val = self.match_keys(self.mode)
        if callable(val):
            val()
            self.logger.debug("Succesfully called shortcut callback")

        if self.mode == Modes.Close:
            self.logger.info("Closing keyboard.Listener() thread")
            return False

    def register_shortcut(self, shortcut: ShortCut) -> None:
        """ If shortcut has callback function that has not yet been passed class instance, class instance is passed.
        :param shortcut: ShorctCut object
        """
        if shortcut.mode not in self.shortcuts:
            raise NotImplemented(f"Mode: {shortcut.mode} is not a currently supported shortcut mode")
        if not shortcut.builtin:
            setattr(self, shortcut.callback.__name__, shortcut.callback)
        self.shortcuts[shortcut.mode].append(shortcut)

    def register_shortcuts(self, shortcuts: list[ShortCut]) -> None:
        for shortcut in shortcuts:
            self.register_shortcut(shortcut)

    def save_fig(self) -> None:
        """ Saves Inkscape figure and converts to pdftex """
        self.logger.info(f"Saving figure: {self.figure_path}")
        self.toggle_mode(Modes.Insert)
        with self.cont.pressed(keyboard.Key.cmd):
            self.cont.tap('s')

        svg_to_pdftex(self.figure_path, self.config['inkscape-exec'], self.config['export-dpi'])

    def match_keys(self, mode: Modes) -> None | Callable:
        """ Implements logic for keys pattern matching.
        :return: key_callback (callable) if list of keys matches pattern else None """
        # Instant reject conditions
        if len(self.pressed) == 0 or mode == Modes.Pause: # Pretty sure there is no need for Modes.Pause
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

    def add_obsever(self, observer) -> None:
        self.observers.append(observer)

    def notify_observers(self) -> None:
        for observer in self.observers:
            observer.update(self.mode.value)


    @staticmethod
    def key_to_str(key: keyboard.Key) -> str:
        """ Simplifies Key__repr__() to a more readable format. ex: "'Key.cmd: key_code'" -> 'cmd' """
        return key.__repr__().replace("'", '').split('.')[-1].split(':')[0]


class StatusWindow:
    """ MacOS sonoma => warning message displayed when pygui window is created
    - Currently supressing warning
    """
    def __init__(self, height: int = 30, width: int = 150) -> None:
        self.root = tk.Tk()
        self.root.geometry(f"{width}x{height}+{self.root.winfo_screenheight()}+{0}")
        self.status_label = tk.Label(self.root, text="waiting")
        self.queue = queue.Queue()
        self.logger = logging.getLogger(__name__ + "StatusWindow")
        self.current_mode = None
        self.runnig = True
        self.status_label.pack()

    def retreive_mode(self) -> Modes | None:
        try:
            mode = self.queue.get_nowait()
            return mode
        except queue.Empty:
            return None

    def update(self, state) -> None:
        self.queue.put(state)

    def close(self) -> None:
        self.runnig = False
        self.logger.info("Closing gui window and exiting mainloop")
        self.root.destroy()
        self.root.quit()


    def inizialize(self) -> None:
        """ Inizialize gui mainloop then start gui logic thread """
        thread = threading.Thread(target=self.after)
        self.root.after(1000,thread.start)
        self.root.mainloop()

    def after(self) -> None:
        """ Logic loop for updating gui mode label. Called after mainloop() is started """
        if self.runnig:
            res = self.retreive_mode()
            if res != None and res != self.current_mode:
                self.current_state = res
                self.change_mode(self.current_state.value)
                self.logger.debug(f"Gui received message: '{res}'")

            if self.current_state == "close":
                self.close()

            else:
                self.root.after(1000, self.after)


    def change_mode(self, mode: str) -> None:
        self.status_label.config(text=mode)
