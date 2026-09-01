import platform
from functools import partial
import subprocess

from .compiler import StandaloneSourceFile, compile_source, CompileOptions, OutputFormat
from ..config import CONFIG

def open_cmd() -> str:
    """
    Returns the open command for the respective operating system
    """
    system_name = platform.system().lower()
    if system_name == "darwin":
        cmd = "open"
    elif system_name == "linux":
        cmd = "xdg-open"
    else:
        cmd = "start"
    return cmd

def open_pdf(source: StandaloneSourceFile, lazy: bool=True) -> int:
    pdf_path = source.pdf_path()
    if pdf_path is None or lazy is False:
        options = CompileOptions(source.path, output_format=OutputFormat.PDF)
        compile_source(source, options)

        pdf_path = source.pdf_path()
        if pdf_path is None:
            return False

    open = open_cmd()
    result = subprocess.run([open, pdf_path], stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    return result.returncode

#def open_file_with_editor(filename: str) -> None:
#    import iterm2
#
#    async def _main(connection, filename: str):
#        app = await iterm2.async_get_app(connection)
#        window = app.current_window
#        if window is None: return None
#        new_window = await window.async_create(connection)
#        tab = new_window.tabs[0]
#        session = tab.sessions[0]
#
#        await new_window.async_set_frame(iterm2.Frame(iterm2.Point(500, 500), iterm2.Size(1000, 1000)))
#        await session.async_send_text(f"{CONFIG.editor} {filename}\n")
#
#    main = partial(_main, filename=filename)
#    iterm2.run_until_complete(main)
