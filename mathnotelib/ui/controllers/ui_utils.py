from ..dialog import show_error_dialog
from typing import Callable
from pathlib import Path

def with_error_dialog(func: Callable):
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            win = getattr(self, "window", None)
            if win is not None:
                show_error_dialog(win, str(e))
    return wrapper


def rendered_sorted_key(path: Path) -> int:
    num = int(path.name.split(".")[0].split("-")[1])
    return num

