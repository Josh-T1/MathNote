from pathlib import Path
from PyQt6.QtCore import Qt, QSize

ICON_PATH = Path(__file__).parent / "icons"

ICON_SIZE = QSize(30, 30)

OUTPUT_FILE_STEM = "rendered"
TYP_FILE_LIVE = "/tmp/live.typ"
SVG_FILE_LIVE = "/tmp/live.svg"
VIEWER_HEIGHT = 985
VIEWER_WIDTH = 800
LABEL_HEIGHT = 30

FILE_ROLE = Qt.ItemDataRole.UserRole + 1
DIR_ROLE = Qt.ItemDataRole.UserRole + 2
LOADED_ROLE = Qt.ItemDataRole.UserRole + 3
COURSE_CONTAINER_ROLE = Qt.ItemDataRole.UserRole + 4
EMPTY = Qt.ItemDataRole.UserRole + 5
