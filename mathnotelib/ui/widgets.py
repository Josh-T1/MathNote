from pathlib import Path
from typing import Iterable, Optional
import json

from PyQt6 import QtCore
from PyQt6.QtGui import QFontMetrics, QIcon, QStandardItemModel
from PyQt6.QtCore import  QModelIndex, Qt, pyqtBoundSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QStackedWidget, QWidget

from .style import BOXED_LABEL_CSS, LABEL_CSS
from .constants import ICON_PATH, FILE_ROLE, DIR_ROLE, COURSE_DIR, COURSE_CONTAINER_ROLE, LABEL_HEIGHT
from ..models import Category, Note
from ..services import NotesRepository

class StandardItemModel(QStandardItemModel):
    def __init__(self, parent=None):
        self.move_signal: None | pyqtBoundSignal = None
        super().__init__(parent=parent)
        self.pending: dict | None=None
        self.drag_source = {}

    def mimeData(self, indexes: Iterable[QtCore.QModelIndex]) -> Optional[QtCore.QMimeData]:
        mime_data = super().mimeData(indexes)
        idx = list(indexes)[0]
        self.drag_source["row"] = idx.row()
        self.drag_source["parent"] = idx.parent()

        item = self.itemFromIndex(idx)
        if item is None:
            return super().mimeData(indexes)


        maybe_note = item.data(FILE_ROLE)
        maybe_cat = item.data(DIR_ROLE)

        if isinstance(maybe_cat, Category) and mime_data:
            data = {
                    "path": NotesRepository.category_to_path(maybe_cat),
                    "type": "Category",
                    }
            serialized = json.dumps(data).encode('utf-8')
            mime_data.setData("application/x-note-paths", serialized)
            return mime_data

        if isinstance(maybe_note, Note) and mime_data:
            data = {
                    "path": NotesRepository.note_to_path(maybe_note),
                    "type": "Note",
                    }
            serialized = json.dumps(data).encode('utf-8')
            mime_data.setData("application/x-note-paths", serialized)
        return mime_data

    def dropMimeData(self, data: Optional[QtCore.QMimeData], action: QtCore.Qt.DropAction, row: int, column: int, parent: QtCore.QModelIndex) -> bool:
        if self.move_signal is not None and data is not None and data.hasFormat("application/x-note-paths"):
            json_bytes = data.data("application/x-note-paths")
            json_string = json_bytes.data().decode('utf-8')
            d = json.loads(json_string)
            self.pending = {
                    "data": data,
                    "action": action,
                    "row": row,
                    "column": column,
                    "parent": parent
                    }
            self.move_signal.emit(d, parent)
            return False
        return super().dropMimeData(data, action, row, column, parent)

    def complete_move(self) -> bool:
        if self.pending:
            pending = self.pending
            self.pending = None
            result = super().dropMimeData(
                    pending["data"],
                    pending["action"],
                    pending["row"],
                    pending["column"],
                    pending["parent"]
                    )
            if result and self.drag_source['parent'].isValid():
                self.removeRow(self.drag_source['row'], self.drag_source['parent'])
            elif result:
                self.removeRow(self.drag_source['row'])
            return result

        return False

    def hasChildren(self, parent: QModelIndex=QModelIndex()) -> bool:
        if (parent.isValid() is False or # Delete?
            parent.data(DIR_ROLE) or
            parent.data(COURSE_DIR) is not None
            ):
            return True
        return super().hasChildren(parent)


class TightStackedWidget(QStackedWidget):
    def sizeHint(self):
        w = self.currentWidget()
        return w.sizeHint() if w else super().sizeHint()

    def minimumSizeHint(self):
        w = self.currentWidget()

        return w.minimumSizeHint() if w else super().minimumSizeHint()

    def maximumSize(self):
        w = self.currentWidget()
        return w.maximumSize() if w else super().maximumSize()

class PathLabel(QWidget):
    def __init__(self):
        super().__init__()
#        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.initUi()

    def initUi(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel()
        self._warning_icon = QLabel()

        self.label.setStyleSheet(BOXED_LABEL_CSS)
        self.label.setFixedHeight(LABEL_HEIGHT)
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._warning_icon.setPixmap(QIcon(str(ICON_PATH / "warning.png")).pixmap(16, 16))
        self._warning_icon.setFixedSize(16, 16)
#        self._warning_icon.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._warning_icon.hide()

        layout.addWidget(self.label, stretch=1)
#        layout.addStretch()
        layout.addWidget(self._warning_icon)
        self.setLayout(layout)

    def set_path(self, path: str):
        self._full_path = path if path != "None" and len(path) > 0 else "Invalid Path"
        self.label.setText(path)
        is_valid = Path(path).exists() if path else True  # decide: empty path = valid or invalid?
        self._warning_icon.setVisible(not is_valid)
        self.setToolTip(self._full_path)

