import collections
import json
from pathlib import Path
from typing import Callable, Iterable, Optional
from PyQt6 import QtCore
from PyQt6.QtGui import QIcon, QStandardItemModel
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtCore import QDataStream, QIODevice, QMimeData, QModelIndex, Qt, pyqtBoundSignal

from mathnotelib._enums import FileType
from mathnotelib.models.note import Note
from mathnotelib.services.course_repo import CourseRepository
from mathnotelib.services.note_repo import NotesRepository

from .style import ICON_CSS, LABEL_CSS, SWITCH_CSS
from . import constants
from ..pipeline import load_macros, get_hack_macros
from ..config import CONFIG
from ..flashcard import FlashcardMainWindow, FlashcardSession, FlashcardController
from ..services import FlashcardCompiler
from ..models import SourceFile, Course, Category


def confirm_delete(window: QWidget, item: SourceFile | Course | Category) -> bool:
    """
    Show a confirmation dialog before deleting.

    Args:
        parent: Parent widget (e.g. main window).
        name: Name of the object to delete.
        kind: Type of object (e.g. "note", "course", "file").

    Returns:
        True if user confirmed, False otherwise.
    """
    msg = QMessageBox(window)
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setWindowTitle(f"Delete {item.name}")
    msg.setText(f"Are you sure you want to delete the {type(item).__name__} '{item.name}'?")
    msg.setInformativeText("This action cannot be undone.")
    msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
    msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
    result = msg.exec()
    return result == QMessageBox.StandardButton.Yes


class ModeSelector(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.btn_preview = QPushButton("Preview")
        self.btn_editor = QPushButton("Editor")
        self.btn_label = QLabel("Document Mode")
        self.btn_label.setStyleSheet(LABEL_CSS)
        main_layout = QVBoxLayout()
        btn_widget = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(0)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        for btn in (self.btn_editor, self.btn_preview):
            btn.setCheckable(True)
            btn.setFlat(True)
            btn.setStyleSheet(SWITCH_CSS)
            btn.setFixedHeight(constants.LABEL_HEIGHT)
            btn_layout.addWidget(btn)
            self.btn_group.addButton(btn)

        self.btn_preview.setChecked(True)
        btn_widget.setLayout(btn_layout)
        main_layout.addWidget(self.btn_label, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(btn_widget)
        self.setLayout(main_layout)

    def connect_mode_btn(self, callback: Callable[[str], None]):
        self.btn_group.buttonClicked.connect(lambda btn: callback(btn.text()))


def build_dragged_tree(indexes: list[QModelIndex]):
    index_set = set(indexes)
    root = None
    for idx in indexes:
        parent = idx.parent()
        while parent.isValid() and parent in index_set:
            parent = parent.parent()

        if parent not in index_set:
            root = idx
        else:
            root = parent
    return root

def get_indexes_from_mime_data(mime_data: QMimeData, model: QStandardItemModel):
    """
    Reconstruct QModelIndex objects from a QMimeData object for a given model.
    Returns a list of QModelIndex.
    """
    indexes = []

    if not mime_data.hasFormat("application/x-qabstractitemmodeldatalist"):
        return indexes

    data = mime_data.data("application/x-qabstractitemmodeldatalist")
    stream = QDataStream(data, QIODevice.OpenModeFlag.ReadOnly)

    while not stream.atEnd():
        row = stream.readInt32()
        col = stream.readInt32()
        role_count = stream.readInt32()
        # read roles but we don't need them here if just reconstructing index
        for _ in range(role_count):
            stream.readInt32()  # role
            stream.readQVariant()  # value

        # Reconstruct QModelIndex for this row/col in model
        index = model.index(row, col)
        indexes.append(index)
    return indexes


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


# TODO add vim_btn iff users have set editor to vim
class LauncherWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initUI()

    def initUI(self):
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(4)
        row_1 = QHBoxLayout()
        vim_label = QLabel("Editor (vim/nvim)")
        vim_label.setStyleSheet(LABEL_CSS)
        vim_btn = QPushButton()
        vim_btn.setIcon(QIcon(str(constants.ICON_PATH / "vim.png")))
        vim_btn.setStyleSheet(ICON_CSS)
        vim_btn.setFixedSize(constants.ICON_SIZE)

        row_2 = QHBoxLayout()
        launch_label = QLabel("Flashcards")
        flashcard_button = QPushButton()
        flashcard_button.setIcon(QIcon(str(constants.ICON_PATH / "cards.png")))
        flashcard_button.setStyleSheet(ICON_CSS)
        launch_label.setStyleSheet(LABEL_CSS)
        flashcard_button.setFixedSize(constants.ICON_SIZE)

        row_1.addWidget(vim_label)
        row_1.addWidget(vim_btn)
        row_2.addWidget(launch_label)
        row_2.addWidget(flashcard_button)
        self.main_layout.addLayout(row_1)
        self.main_layout.addLayout(row_2)
        flashcard_button.clicked.connect(self.launch_flashcards)

    def launch_vim(self):
        pass

    # TODO ensure that we wait for flashcards to terminate properly
    def launch_flashcards(self):
        macros_path = Path(CONFIG.template_files[FileType.LaTeX]["note_macros"])
        preamble = Path(CONFIG.template_files[FileType.LaTeX]["note_preamble"])
        self.compilation_manager = FlashcardCompiler(macros_path, preamble)
        self.flashcard_model = FlashcardSession(self.compilation_manager)
        self._window = FlashcardMainWindow()
        self.controller = FlashcardController(self._window, self.flashcard_model, CONFIG) #type: ignore
        self._window.setCloseCallback(self.controller.close)
        self.controller.run()
