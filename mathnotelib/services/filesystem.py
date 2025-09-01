import platform

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
