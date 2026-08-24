from typing import Iterable, Optional
import json

from PyQt6 import QtCore
from PyQt6.QtGui import QStandardItemModel
from PyQt6.QtCore import  QModelIndex, pyqtBoundSignal
from PyQt6.QtWidgets import QStackedWidget


from . import constants
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


        maybe_note = item.data(constants.FILE_ROLE)
        maybe_cat = item.data(constants.DIR_ROLE)

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
            parent.data(constants.DIR_ROLE) or
            parent.data(constants.COURSE_DIR) is not None
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
