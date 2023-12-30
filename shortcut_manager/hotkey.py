import subprocess
import sys
import os
sys.path.insert(0, '../')
from config import get_config
from pynput import keyboard
import Quartz
from vim import write_latex
from utils import focus
from figures import svg_to_pdftex

def r_darwin_intercept(event_type, event):
    length, chars = Quartz.CGEventKeyboardGetUnicodeString(event, 100, None, None)

    if length > 0 and chars == 'x':
        # Suppress x
        return None
    elif length > 0 and chars == 'a':
        # Transform a to b
        Quartz.CGEventKeyboardSetUnicodeString(event, 1, 'b')
    else:
        return event


class ShortCutManager():
    def __init__(self, config:dict, figure_path: str):
        self.normal = False
        self.config = config
        self.patterns = self._get_patterns()
        self.pressed = []
        self.figure_path = figure_path
        #self.hotkeys = self._get_hotkeys()
        self.cont = keyboard.Controller()


    def listen(self):
        try:
            with keyboard.Listener(on_press=self.on_press, on_release=self.on_release, darwin_intercept=self.darwin_intercept) as l:
                l.join()
        except KeyboardInterrupt:
            self.close()

    def togle_mode(self):
        self.normal = not self.normal

    def darwin_intercept(self, event_type, event):
        if self.normal:
            return None
        else:
            return event

    def on_press(self, key):
        self.pressed.append(key)

    def on_release(self, key):
        handled = self.handle(key)
        if handled:
            self.pressed.clear()

    @staticmethod
    def key_to_str(key: keyboard.Key):
        return key.__repr__().replace("'", '').split('.')[-1].split(':')[0]

    def handle(self, key):
        if key == keyboard.Key.esc:
            self.togle_mode()
            return True

        if not self.normal:
            return True
        string = '+'.join([self.key_to_str(k) for k in self.pressed])
        if string in self.patterns.keys():
            self.patterns[string]()
            return True

        for key in self.patterns.keys():
            if string in key:
                return False
        return True

    def save_fig(self):
        self.togle_mode()
        with self.cont.pressed(keyboard.Key.cmd):
            self.cont.tap('s')
        svg_to_pdftex(self.figure_path)

#        if Path(self.figure_path).stem == Path(config['figure-template']).stem: # do i need to save as everytime
#            p = subprocess.Popen(
#                    ['pbcopy'],
#                    stdin=subprocess.PIPE,
#                    stdout=subprocess.DEVNULL,
#                    stderr=subprocess.DEVNULL
#                    )
#            p.communicate(input=bytes(self.config["figure-path"], encoding='utf-8'))
#            self.cont.tap(keyboard.Key.right)
#            with self.cont.pressed(keyboard.Key.ctrl, keyboard.Key.shift):
#                self.cont.tap('v')
#            self.cont.tap(keyboard.Key.delete)
#
#            with self.cont.pressed(keyboard.Key.cmd):
#                self.cont.tap('v')
#            self.cont.tap(keyboard.Key.enter)
#            self.cont.tap(keyboard.Key.enter)

    def close(self):
        with open(self.config['.data'], mode='r+') as f:
            files  = f.read().split('\n')
            f.truncate(0)
            f.seek(0)
        for file in files:
            if file != '':
                os.remove(file)
        quit()

    def add_latex(self):
        wrote = write_latex()
        focus("Inkscape")
        self.togle_mode()
        if wrote:
            with self.cont.pressed(keyboard.Key.cmd):
                self.cont.tap('v')


    def _get_patterns(self):
        return{
                "t" : self.add_latex,
                "cmd+c" : self.close,
                "cmd+s" : self.save_fig # make this shift
                }


# how can i check if latex is wrote
#if __name__ == '__main__':
#    l = keyboard.KeyCode.from_char("Key.esc")
#    print(l == keyboard.Key.esc)
#    hotkeys = keyboard.GlobalHotkeyboard.Keys({
#        '<esc>' : M.actiavte_I
#        })
