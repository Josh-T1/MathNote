import AppKit
import os
import iterm2
import asyncio
from functools import partial
import logging

INKSCAPE_PATH = "/Applications/Inkscape.app"

if not os.path.exists(INKSCAPE_PATH):
    raise FileNotFoundError(f"{INKSCAPE_PATH} could not be found")

logger = logging.getLogger("ShortCutManager")

def close_app(app_name):
    app = is_app_running(app_name)
    if app:
        app.terminate()

def is_app_running(app_name): # TODO mac specific
    workspace = AppKit.NSWorkspace.sharedWorkspace()
    running_apps = workspace.runningApplications()
    for app in running_apps:
        if app.localizedName() == app_name:
            return app
    return None

def bring_app_to_foreground(app_name): # TODO macOS specific
    app = is_app_running(app_name)
    if app:
        app.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)

async def get_num_windows(app) -> int:
    return len(app.terminal_windows)

async def _main(connection, filename: str) -> None:
    """ From Iterm2 Api. Opens nvim in a new Iterm2 instance and pauses code execution untill the window is closed.
    filename: nvim
    connection: ?
    """
    app = await iterm2.async_get_app(connection)
    window = app.current_window
    if window is None:
        raise Exception("Windown is none")

    num_windows = await get_num_windows(app)
    new_window = await window.async_create(connection, command=f"/bin/bash -l -c 'nvim {filename}'")
    await new_window.async_set_frame(iterm2.Frame(iterm2.Point(500,500), iterm2.Size(600, 100)))
#    focus("Iterm") # there is an error with this

    while await get_num_windows(app) > num_windows:
        await asyncio.sleep(0.1)

def promt_user_for_latex(file_path: str) -> None:
    """ runs _main
    :param file_path: file_path for file being opened with vim inside iterm2 """
    #file_path = "/Users/joshuataylor/desktop/test.txt"
    if not os.path.isfile(file_path):
        logger.error(f"Invalid path: {file_path}")
        raise  ValueError("Invalid file path: {file_path}")

    main = partial(_main, filename=file_path)
    iterm2.run_until_complete(main)

def set_png_to_clipboard(png_path):
    """ Chat Gpt wrote this... hopefully this works fine. An alternative approach:
    subprocess.run(
            ["osascript", "-e", f'set the clipboard to (read (POSIX file "{tmpfile.name}.png") as  {{«class PNGf»}})'],
            )
        """
    # Create an NSPasteboard instance
    pasteboard = NSPasteboard.generalPasteboard()

    # Clear the current contents of the pasteboard
    pasteboard.clearContents()

    # Load the PNG image from the file
    image = NSImage.alloc().initWithContentsOfFile_(png_path)
    if image is None:
        print("Failed to load image.")
        return

    # Create an NSData object from the NSImage
    tiff_data = image.TIFFRepresentation()
    if tiff_data is None:
        print("Failed to get TIFF representation of image.")
        return

    # Create an NSBitmapImageRep from the TIFF data
    bitmap = AppKit.NSBitmapImageRep.alloc().initWithData_(tiff_data)
    if bitmap is None:
        print("Failed to create NSBitmapImageRep from TIFF data.")
        return

    # Convert the NSBitmapImageRep to PNG data
    png_data = bitmap.representationUsingType_properties_(AppKit.NSPNGFileType, None)
    if png_data is None:
        print("Failed to create PNG data from NSBitmapImageRep.")
        return

    # Set the PNG data to the clipboard
    success = pasteboard.setData_forType_(png_data, NSPasteboardTypePNG)
    if not success:
        print("Failed to set PNG data to clipboard.")
    else:
        print("PNG data successfully set to clipboard.")
