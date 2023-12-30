import iterm2
from functools import partial
import sys
import os
import time
from utils import focus

def get_num_windows(app):
    return len(app.terminal_windows)


async def _main(connection, filename: str):
    app = await iterm2.async_get_app(connection)
    window = app.current_window

    if window is not None:
        new_window = await window.async_create(connection, command=f"/bin/bash -l -c 'nvim {filename}'")
        await new_window.async_set_frame(iterm2.Frame(iterm2.Point(500,500), iterm2.Size(600, 100)))
        focus("Iterm")
        # This is a questionable way to keep script running while user writes latex, hack solution for vim.py
        num_windows = 2
        while num_windows > 1:
            time.sleep(0.1)
            app = await iterm2.async_get_app(connection)
            num_windows = get_num_windows(app)
    else:
        print("No current window")
#    await window.async_set_frame()
def run():
    #file_path = "/Users/joshuataylor/desktop/test.txt"
    file_path = sys.argv[1]
    if os.path.isfile(file_path):
        main = partial(_main, filename=file_path)
        iterm2.run_until_complete(main)

    else:
        raise  ValueError("Invalid file Path")


if __name__ == '__main__':
    run()
