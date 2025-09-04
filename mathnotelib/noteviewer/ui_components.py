from typing import Callable
from PyQt6.QtGui import QIcon, QStandardItemModel
from PyQt6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtCore import QModelIndex, Qt

from .style import ICON_CSS, LABEL_CSS, SWITCH_CSS
from . import constants
from ..config import CONFIG
from ..flashcard import FlashcardMainWindow, FlashcardModel, FlashcardController
from ..services import CompilationManager
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

class StandardItemModel(QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def hasChildren(self, parent: QModelIndex=QModelIndex()) -> bool:
        if (parent.isValid() is False or # Delete?
            parent.data(constants.DIR_ROLE) or
            parent.data(constants.COURSE_DIR) is True
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
        self.compilation_manager = CompilationManager()
        self.flashcard_model = FlashcardModel(self.compilation_manager)
        self._window = FlashcardMainWindow()
        self.controller = FlashcardController(self._window, self.flashcard_model, CONFIG) #type: ignore
        self._window.setCloseCallback(self.controller.close)
        self.controller.run(None)
