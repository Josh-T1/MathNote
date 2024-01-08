import os
import logging
import multiprocessing as mp
from re import sub
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

class IK_ShortcutManager():
    def __init__(self, config: dict, figure_path: str, key_handler, gui_queue: Optional[mp.Queue]):
        """ Shortcuts can not contain esc character or 'i'.
        config: config dictionary
        figure_path: is the desired save location for inkscape figure
        subprocess_queue: subprocess's are put into subprocess_queue where they are executed in another thread
        """
        self.logger = logging.getLogger(__name__ + "ShortcutManager")
        self.shortcuts = {"normal": {}, "insert": {}}

        self.gui_queue = gui_queue
        self.key_handler = key_handler(self.shortcuts)
        self._set_sane_defaults()

        self.config = config
        self.figure_path = figure_path
        self.cont = keyboard.Controller()
        self.mode = Modes.Insert

        self.toggle_mode(Modes.Insert) #hack solution to update gui



    def _set_sane_defaults(self):
        # I THINK THIS IS BREAKING MY PROGRAM
        self.register_shortcuts([
                ("cmd+c", self.close, "normal", True),
                ("esc", partial(self.toggle_mode, mode=Modes.Normal), "insert", True),
                ('i', partial(self.toggle_mode, mode=Modes.Insert), "normal", True),
                ('t', self.add_latex, "normal", True)
                # , how do i allow pausing?
                ])

    def start(self):
        """ Creates keyboard.Listener() and starts thread """
        self.listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release, darwin_intercept=self._darwin_intercept)
        self.logger.info("Listener thread is starting")
        self.listener.start()

    def join(self):
        """ impliments threading.Thread().join() """
        try:
            self.listener.join()
        except KeyboardInterrupt:
            self.logger.warning("Shortcut Manager was stopped with a KeyboardInterrupt")
            self.close()

    def close_listener(self):
        """ Terminates self.listener thread """
        self.listener.stop()
        self.toggle_mode(Modes.Pause)

    def close(self):
        self.logger.info("Starting ShortcutManager close")
        self._delete_tmp_files()
        self.save_fig()
        self.close_listener()

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
        """ Change object mode state and notify gui window through the queue """
        self.mode = mode
        if self.gui_queue != None:
            self.gui_queue.put(self.mode.value)

    def _darwin_intercept(self, event_type, event):
        """ Allows for keys to be intercepted and blocked from being sent to stdout if mode=normal. Darwing_intercept is MacOS specific """
#        if self.mode == Modes.Pause: return event
        if self.mode == Modes.Normal:
            return None
        else:
            return event

    def _on_press(self, key) -> None:
        self.key_handler.pressed_key(key)

    def _on_release(self, key: keyboard.Key) -> Union[bool, None]: # make sure closing the __enter__ condition trigers __exit__
        """ Returning False stops keyboard.Listener() """
        val = self.key_handler.handle(self.mode, key)
        if callable(val):
            val()
            self.logger.debug("Succesfully called shortcut handler")

        if self.mode == Modes.Close:
            self.logger.info("Closing keyboard.Listener() thread")
            return False

    def register_shortcut(self, shortcut: str, handler: Callable, mode: str, obj_method: bool):
        """obj_method: True if handler is a class method, else False -> sets handler to class method handler.__name__ """
        if mode not in self.shortcuts:
            self.logger.warning(f"Mode: {mode} is not supported")
            return
        if not obj_method:
            setattr(self, handler.__name__, handler)
#        handler = handler if obj_method else partial(handler, inst=self)
#        if not method:
#            handler = partial(handler, inst=self)
        self.shortcuts[mode][shortcut] = handler
        self.key_handler.register_shortcut(shortcut, handler, mode)

    def register_shortcuts(self, shortcuts: list[tuple]):
        """ Shortcuts: [(shortcut: str, handler: Callable, mode:str),...] """
        for shortcut in shortcuts:
            self.register_shortcut(*shortcut)

    def save_fig(self) -> None:
        self.logger.info(f"Saving figure: {self.figure_path}")
        self.toggle_mode(Modes.Insert)
        with self.cont.pressed(keyboard.Key.cmd):
            self.cont.tap('s')

        #dst = self.figure_path.rsplit('.')[0] + ".pdf"
        svg_to_pdftex(self.figure_path, self.config['inkscape-exec'], self.config['export-dpi'])


    def add_latex(self) -> None:
        """ Launches new Iterm2 instanace from which vim is opened in a tmp file, if latex is written, it is
        compiled and pasted to inkscape
        inst: IK_KeyHandler instance
        """

        self.close_listener()
        subprocess.run(["python3", "/Users/joshuataylor/documents/python/myprojects/mathnote/shortcut_manager/vim.py"])
        self.start()
        self.toggle_mode(Modes.Insert)
        focus("Inkscape")
        with self.cont.pressed(keyboard.Key.cmd):
            self.cont.tap('v')
        self.join()


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


    def handle(self, mode: Modes, key: keyboard.Key) -> Union[None, Callable]:
        """ Rename this """
        # Instant reject conditions
        if len(self.pressed) == 0 or mode == Modes.Pause:
            self.pressed.clear()
            return None

        patterns_mode = self.shortcuts[mode.value]
        pattern = '+'.join(self.pressed)

        for key_ in patterns_mode:
            # Case: full match
            if pattern == key_:
                self.logger.debug(f"Calling shortcut handler for shotcut: {pattern}")
                self.pressed.clear()
                return patterns_mode[pattern]

            # Case: partial match
            if pattern in key_ and pattern != '':
                self.logger.debug(f"Partial match with '{pattern}'")
                return None

        # Case: no match
        self.logger.debug(f"No pattern was found, clearing pressed. Pressed: {self.pressed}, Pattern: {pattern}")
        self.pressed.clear()
        return None

    @staticmethod
    def key_to_str(key: keyboard.Key) -> str:
        """ Simplifies Key__repr__() to a more readable format. ex: "'Key.cmd: key_code'" -> 'cmd' """
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
        self.logger = logging.getLogger(__name__ + "StatusWindow")
        self.current_state = None


    def retreive_mode(self):
        try:
            mode = self.queue.get()
            return mode
        except mp.Queue.empty:
            return None

    def close(self):
        # is there a reason quit() not destroy()
        self.logger.info("Closing gui window")
        self.root.quit()

    def start(self):
        """ inizialize gui mainloop then start gui logic thread """
        thread = threading.Thread(target=self.after)
        self.root.after(1000,thread.start)
        self.root.mainloop()


    def after(self):
        """ Logic loop for updating gui mode label. Called after mainloop() is started """

        while True:
            res = self.retreive_mode()
            if res != None and res != self.current_state:
                self.current_state = res
                self.change_mode(self.current_state)
                self.logger.debug(f"Gui received message: '{res}'")

            if self.current_state == "close": # I shouldnt need this
                break

            time.sleep(1)

        self.close()

    def change_mode(self, mode: str):
        self.status_label.config(text=mode)

# =================================================================
# Shortcut Functions
def add_latex(inst) -> None:
    """ Launches new Iterm2 instanace from which vim is opened in a tmp file, if latex is written, it is
    compiled and pasted to inkscape
    inst: IK_KeyHandler instance
    """
    path = __file__.rsplit('/', 1)[0] + "/vim.py" # assumes these live in same directory
    output = write_latex()
#    output = wrote.stdout.strip()
    focus("Inkscape")

    inst.toggle_mode(Modes.Insert)
    if output == "True":

        with inst.cont.pressed(keyboard.Key.cmd):
            inst.cont.tap('v')


def user_shortcuts():
    """ returns user shortcuts in form of list of tuples """
    return [
            ('t', add_latex, "normal", False)
            ]



#def subporcess_executer(cont: CommunicationController):
#    loop = True
#    while loop:
#        res = cont.get_subprocess()
#        if res is not None:
#            subprocess.run(res)
#        loop = cont.active
#        time.sleep(0.5)


class CommunicationController:
    """ Add events and  **HOW DO I CLOSE**"""
    def __init__(self, gui_queue, subprocess_queue):
        self.gui_queue = gui_queue
        self.subprocess_queue = subprocess_queue
        self.active = True # Does this make sence?

    def get_mode_update(self):
        pass
    def get_message_update(self):
        pass
    def get_subprocess_update(self):
        self.get_item(self.subprocess_queue)

    @staticmethod
    def get_item(queue):
        try:
            res = queue.get()
            return res
        except mp.Queue.empty:
            return None

    def get_subprocess(self):
       return
    def add_event(self, event, event_type=None):
        """ Valid type are 'message', 'subprocess', 'mode' """
        if event_type == "mode":
            self.gui_queue.put(event)
# Add event function
#



