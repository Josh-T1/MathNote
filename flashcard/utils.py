import iterm2
from functools import partial

async def _main(connection, filename):
    app = await iterm2.async_get_app(connection)
    window = app.current_window
    if window is None: return None
    new_window = await window.async_create(connection)
    tab = new_window.tabs[0]
    session = tab.sessions[0]

    await new_window.async_set_frame(iterm2.Frame(iterm2.Point(500, 500), iterm2.Size(1000, 1000)))
    await session.async_send_text(f"nvim {filename}\n")

def open_file_with_vim(filename):
    main = partial(_main, filename=filename)
    iterm2.run_until_complete(main)
