from pathlib import Path

from PyQt6.QtCore import Qt, QSize

from ..utils import config


ROOT_DIR = Path(config["root"])
ICON_PATH = Path(__file__).parent / "icons"

ICON_SIZE = QSize(30, 30)
VIEWER_SIZE = (800, 1000)

OUTPUT_FILE_STEM = "rendered"
TYP_FILE_LIVE = "/tmp/live.typ"
SVG_FILE_LIVE = "/tmp/live.svg"

FILE_ROLE = Qt.ItemDataRole.UserRole + 1
DIR_ROLE = Qt.ItemDataRole.UserRole + 2
LOADED_ROLE = Qt.ItemDataRole.UserRole + 3
COURSE_CONTAINER_ROLE = Qt.ItemDataRole.UserRole + 4

NOTES_DIR = ROOT_DIR / "Notes"

