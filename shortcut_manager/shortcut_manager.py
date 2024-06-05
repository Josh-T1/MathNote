import os
import logging
from collections import UserDict, deque
import queue as queue
from subprocess import call
from pynput import keyboard
from enum import Enum
from typing import Callable
import tkinter as tk
import threading
from functools import partial
from utils import svg_to_pdftex
from dataclasses import dataclass
from filelock import FileLock
from config import LOCK_FILENAME, PIPELINE_FILENAME

logger = logging.getLogger("ShortCutManager")
logger.setLevel(level=logging.DEBUG)

lock = FileLock(LOCK_FILENAME)

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
                 description: str | None = None,
                 contains_subprocess: bool = False
                 ) -> None:
        self.name = name if name != None else pattern
        self.description = description if description != None else pattern
        self.pattern = pattern
        self.callback = callback
        self._mode = mode
        self.builtin = builtin
        self._enabled = True
        self.contains_subprocess = contains_subprocess

    @property
    def mode(self) -> str:
        return self._mode.value

    @property
    def enabled(self) -> bool:
        return self._enabled

    def execute(self) -> None:
        self.callback()

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

class IK_ShortcutManager:
    """
    Info
    """
    def __init__(self, config: dict, figure_path: str):
        """ Shortcuts can not contain esc character or 'i'.
        :param config: config dictionary
        :param figure_path: save location for figure (path)
        """
        self.logger = logging.getLogger(__name__ + "ShortcutManager")
        self.shortcuts: dict[str, list] = {"normal": [], "insert": []}
        self.pressed: list[str] = []
        self.observers: list = []
        self.config: dict = config
        self.figure_path: str = figure_path
        self.cont: keyboard.Controller = keyboard.Controller()
        self.mode = Modes.Insert
        self.shortcut_in_progress: bool = False
        self.callable_queue = deque()
        self._set_sane_defaults()

    def _set_sane_defaults(self):
        self.register_shortcuts([
                (ShortCut("cmd+c", self.close, Modes.Normal, builtin=True, name="Close")),
                (ShortCut("esc", partial(self.toggle_mode, mode=Modes.Normal), Modes.Insert, builtin=True, name = "NormalMode")),
                (ShortCut("i", partial(self.toggle_mode, mode=Modes.Insert), Modes.Normal, builtin=True, name = "InsertMode")),
                ])

    def start(self):
        """ Creates keyboard.Listener() and starts thread """
        self.listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release, darwin_intercept=self._darwin_intercept)
        self.logger.info("Listener thread is starting")
        self.listener.start()

    def join(self):
        """ Implements threading.Thread().join() """
        try:
            self.listener.join()
        except KeyboardInterrupt as e:
            self.logger.warning(f"ShortcutManager interupted: {e}")
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
        return event

    def _on_press(self, key: keyboard.Key) -> None:
        """ Callback for action key pressed
        :param key: passed by keyboard.Listener
        """
        self.logger.debug(f"key pressed: {self.key_to_str(key)}")
        self.pressed.append(self.key_to_str(key))

    def _on_release(self, key: keyboard.Key) -> bool | None:
        """ Callback upon key release
        :param key: passed by keyboard.Listener
        :returns: None or bool. Returning False stops keyboard.Listener()
        """
        self.match_keys(self.mode)

        if self.callable_queue and not self.shortcut_in_progress:
            callable_ = self.callable_queue.popleft()

            if type(callable_) == ShortCut:
                callable_.execute()
                self.logger.debug(f"Calling shortcut {callable_} with callback: {callable_.callback}, {self.shortcut_in_progress}")

                if callable_.contains_subprocess:
                    self.shortcut_in_progress = True
                    self.logger.debug("starting communication with subprocess")
                    thread = threading.Thread(target=self.communicate_status)
                    thread.start()
            else:
                self.logger.debug(f"Calling function: {callable_}")
                callable_()

        if self.mode == Modes.Close:
            self.logger.info("Closing keyboard.Listener() thread")
            return False

    def communicate_status(self):
        """  """
        while True and self.mode != Modes.Close:
            lock.acquire()
            try:
                with open(PIPELINE_FILENAME, "r+") as file:
                    contents = file.read() # contents display error message
                    if contents:
                        self.logger.debug(f"Subprocess termination message: {contents}")
                        self.shortcut_in_progress = False
                        file.truncate(0)
                        file.seek(0)
                        break
            finally:
                lock.release()

    def register_shortcut(self, shortcut: ShortCut) -> None:
        """ If shortcut has callback function that has not yet been passed class instance, class instance is passed.
        :param shortcut: ShorctCut object
        """
        if shortcut.mode not in self.shortcuts:
            raise NotImplementedError(f"Not supported mode: {shortcut.mode}")
        if not shortcut.builtin:
            shortcut.callback = partial(shortcut.callback, self)
        self.shortcuts[shortcut.mode].append(shortcut)

    def register_shortcuts(self, shortcuts: list[ShortCut]) -> None:
        for shortcut in shortcuts:
            self.register_shortcut(shortcut)

    def save_fig(self) -> None:
        """ Saves Inkscape figure and converts to pdftex
        """
        self.logger.info(f"Saving figure: {self.figure_path}")
        self.toggle_mode(Modes.Insert)
        with self.cont.pressed(keyboard.Key.cmd):
            self.cont.tap('s')
        svg_to_pdftex(self.figure_path, self.config['inkscape-exec'], self.config['export-dpi'])

    def match_keys(self, mode: Modes) -> None:
        """ Implements logic for keys pattern matching.
        :return: key_callback (callable) if list of keys matches pattern else None """
        # Instant reject conditions
        if len(self.pressed) == 0 or self.shortcut_in_progress:
            self.pressed.clear()
            return None

        shortcuts_target_mode = self.shortcuts[mode.value]
        pattern = '+'.join(self.pressed)

        for shortcut in shortcuts_target_mode:
            if not shortcut.enabled: # Some shortcuts may 'disable' others. ie) latex shortcut pauses 'esc' shortcut so that writing to file in vim is possible
                continue

            key_ = shortcut.pattern
            # Case: full match
            if pattern == key_:
                self.callable_queue.append(shortcut)
                self.pressed.clear()
                return None

            # Case: partial match
            if key_.startswith(pattern) and pattern != '': # changed from pattern in key_. Test this
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
        """ Simplifies Key__repr__() to a more readable format. ex: "'Key.cmd: key_code'" -> 'cmd'
        TODO: figure out what keycodes are..."""
        return key.__repr__().replace("'", '').split('.')[-1].split(':')[0]


class StatusWindow:
    """ MacOS sonoma warning:
    WARNING: Secure coding is not enabled for restorable state! Enable secure coding by
    implementing NSApplicationDelegate.applicationSupportsSecureRestorableState: and returning YES.
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

    def retreive_mode(self) -> str | None:
        try:
            mode = self.queue.get_nowait()
            return mode
        except queue.Empty:
            return None

    def update(self, state) -> None:
        self.queue.put(state)

    def close(self) -> None:
        self.runnig = False
        self.logger.debug("Closing gui window and exiting mainloop")
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
                self.current_mode = res
                self.change_mode(self.current_mode)
                self.logger.debug(f"Gui received message: '{res}'")

            if self.current_mode == "close":
                self.close()

            else:
                self.root.after(500, self.after)

    def change_mode(self, mode: str) -> None:
        self.status_label.config(text=mode)
