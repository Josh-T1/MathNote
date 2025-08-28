from typing import Any, Literal, Protocol, Callable, Optional

from PyQt6.QtGui import QBrush, QIcon, QMouseEvent, QPalette, QStandardItem, QStandardItemModel, QTransform
from PyQt6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame, QGestureEvent, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow, QPinchGesture, QPushButton, QRadioButton, QScrollArea, QSizePolicy,
                             QSpacerItem, QStackedWidget, QStyle, QStyleOptionViewItem, QToolBar, QTreeView, QVBoxLayout, QWidget)
from PyQt6.QtCore import QEvent, QFileSystemWatcher, QLine, QModelIndex, QProcess, QSize, QTimer, pyqtSignal, Qt

from mathnotelib.structure.courses import Course

from .style import ICON_CSS, LABEL_CSS, SWITCH_CSS, TREE_VIEW_CSS
from . import constants
from ..utils import FileType, CONFIG
from ..structure import NotesManager, Courses, Category, OutputFormat, CompileOptions, SourceFile,Note
from ..flashcard import FlashcardMainWindow, CompilationManager, FlashcardModel, FlashcardController



class StandardItemModel(QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def hasChildren(self, parent: QModelIndex=QModelIndex()) -> bool:
        if not parent.isValid():
            return True
        return super().hasChildren(parent)
#        parent = QModelIndex()
#        if not parent.isValid():
#            print("not valid")
#            return True
#        is_fake = parent.data(constants.EMPTY)
#        if is_fake is True:
#            return True


class NameDialog(QDialog):
    def __init__(self, title: str | None=None):
        super().__init__()
        self.title = title
        self.initUI()

    def initUI(self):
        layout = QFormLayout()
        self.setLayout(layout)
        if self.title is not None:
            self.setWindowTitle(self.title)
        self.name = QLineEdit()
        layout.addRow("Name:", self.name)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        return self.name.text()



class NewNoteDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QFormLayout()
        self.setLayout(layout)
        self.name = QLineEdit()
        layout.addRow("Name:", self.name)
        self.ftype_combo = QComboBox()
        self.ftype_combo.addItems(["Typst", "LaTeX"])
        layout.addRow("File Type", self.ftype_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def get_data(self):
        ftype = FileType.LaTeX if self.ftype_combo.currentText() == "LaTeX" else FileType.Typst
        return self.name.text(), ftype

class DaysOfWeekSelector(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        self.checkboxes = {}
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for d in days:
            cb = QCheckBox(d)
            layout.addWidget(cb)
            self.checkboxes[d] = cb

    def get_selected_days(self) -> list:
        return [day for day, cb in self.checkboxes.items() if cb.isChecked()]

    def set_selected_days(self, days):
        for d, cb in self.checkboxes.items():
            cb.setChecked(d in days)

# TODO add ...
class LauncherWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.setContentsMargins(0, 0, 0, 0)
        self.initUI()

    def initUI(self):
        row = QHBoxLayout()
        launch_label = QLabel("Flashcards")
        flashcard_button = QPushButton()
        flashcard_button.setIcon(QIcon(str(constants.ICON_PATH / "cards.png")))
        flashcard_button.setStyleSheet(ICON_CSS)
        launch_label.setStyleSheet(LABEL_CSS)
        flashcard_button.setFixedSize(constants.ICON_SIZE)
        row.addWidget(launch_label)
        row.addWidget(flashcard_button)
        self.main_layout.addLayout(row)
        flashcard_button.clicked.connect(self.launch_flashcards)

    # TODO ensure that we wait for flashcards to terminate properly
    def launch_flashcards(self):
        self.compilation_manager = CompilationManager()
        self.flashcard_model = FlashcardModel(self.compilation_manager)
        self._window = FlashcardMainWindow()
        self.controller = FlashcardController(self._window, self.flashcard_model, CONFIG) #type: ignore
        self._window.setCloseCallback(self.controller.close)
        self.controller.run(None)


class Navbar(QWidget):
    file_opened = pyqtSignal(SourceFile)
    new_note = pyqtSignal()
    new_folder = pyqtSignal()
    new_course = pyqtSignal()
    delete = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tree_visible: bool = True
        self.root_course_cat = NotesManager.build_root_category(CONFIG.root_path / "Notes")
        self.root_notes_item = QStandardItem(self.root_course_cat.name)
        self.root_course_item = QStandardItem("Courses")
        self.initUI()


    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 8, 5, 8)
        main_layout.setSpacing(4)
        self.setLayout(main_layout)
        self.setFixedWidth(200)
        #Init widgets
        self.minimize_button = QPushButton()
        self.new_note_btn = QPushButton()
        self.new_folder_btn = QPushButton()
        self.search_btn = QPushButton()
        self.trash_btn = QPushButton()
        self.mode_selector = ModeSelector()
        self.model = StandardItemModel()
        self.tree = QTreeView()
        self.root_item = self.model.invisibleRootItem()
        self.launcher_widget = LauncherWidget()
        self.menu_bar_layout = QHBoxLayout()

        #Configure
        icons = [(self.minimize_button, "sidebar_left.png"),
                 (self.new_folder_btn, "add_folder.png"),
                 (self.new_note_btn, "new_note.png"),
                 (self.search_btn, "search.png"),
                 (self.trash_btn, "trash.png")
                 ]
        for icon, icon_name in icons:
            icon.setIcon(QIcon(str(constants.ICON_PATH / icon_name)))
            icon.setFixedSize(constants.ICON_SIZE)
            icon.setStyleSheet(ICON_CSS)

        self.tree.setModel(self.model)
        self.tree.setFrameShape(QFrame.Shape.NoFrame)
        self.tree.expanded.connect(self._expand_callback)
        self.tree.setStyleSheet(TREE_VIEW_CSS)
        self.tree.clicked.connect(self._item_clicked_callback)
        if (header := self.tree.header()) is not None:
            header.hide()
        self.minimize_button.setToolTip("Close Sidebar")
        self.new_folder_btn.setToolTip("New Note Folder")
        self.new_note_btn.setToolTip("New Note")
        self.search_btn.setToolTip("Search")
        self.trash_btn.setToolTip("Delete")
        self.new_folder_btn.clicked.connect(self.new_folder.emit)
        self.new_note_btn.clicked.connect(self.new_note.emit)
        self.trash_btn.clicked.connect(self.delete.emit)

        # Add to layout
        buttons = [self.minimize_button, self.new_note_btn, self.new_folder_btn, self.trash_btn, self.search_btn]
        for btn in buttons:
            self.menu_bar_layout.addWidget(btn)
        self.menu_bar_layout.addSpacerItem(QSpacerItem(15, 15, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        main_layout.addLayout(self.menu_bar_layout)
        main_layout.addWidget(self.tree)
        main_layout.addWidget(self.mode_selector)
        main_layout.addWidget(self.launcher_widget)

        self.populate_tree()

#    def add_category(self, cat: QStandardItem, parent: QStandardItem):
#        parent.appendRow(cat)

    def _expand_callback(self, index: QModelIndex):
        # Remark: the item will originally expand with the placeholder element. Once this occurs
        # we will remove placeholder and populate with correct options.
        item = self.model.itemFromIndex(index)
        if item is None:
            return
        cat = item.data(constants.DIR_ROLE)
        loaded = item.data(constants.LOADED_ROLE)
        if cat is not None and loaded is False:
            self._load_item(item, cat)

    def _toggle_tree(self, idx: QModelIndex) -> None:
        if self.tree.isExpanded(idx):
            self.tree.collapse(idx)
        else:
            self.tree.expand(idx)

    def _item_clicked_callback(self, index: QModelIndex):
        item = self.model.itemFromIndex(index)
        if item is None:
            return

        # TODO: handle failed compilation
        if item.data(constants.FILE_ROLE) is not None:
            file: SourceFile = item.data(constants.FILE_ROLE)
            self.file_opened.emit(file)
        # For any item with this role we must do 2 things:
        #   1. Check to see if we should expand or collapse tree around item
        #   2. Check if subcategories and notes have been load. If not, load data and populate rows.
        elif item.data(constants.DIR_ROLE) is not None:
            loaded = item.data(constants.LOADED_ROLE)
            if loaded is False:
                cat: Category = item.data(constants.DIR_ROLE)
                self._load_item(item, cat)
            self._toggle_tree(index)

        elif item.data(constants.COURSE_CONTAINER_ROLE) is not None:
            self._toggle_tree(index)


    def _load_item(self, item: QStandardItem, cat: Category):
        # Check for placeholder row
#        if (c1 := item.child(0)):
#            if c1.text() == "placeholder" and len(cat.children()) > 0:
#                item.removeRow(0)
#        if len(cat.notes()) > 0:
#            item.setData(False, constants.EMPTY)

        for sub_cat in cat.children():
            sub_cat_item = QStandardItem(sub_cat.name)
            sub_cat_item.setFlags(sub_cat_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            sub_cat_item.setData(sub_cat, constants.DIR_ROLE)
            sub_cat_item.setData(False, constants.LOADED_ROLE)

            item.appendRow(sub_cat_item)

        for note in cat.notes():
            note_item = QStandardItem(note.name)
            note_item.setFlags(note_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            note_item.setData(note, constants.FILE_ROLE)
            item.appendRow(note_item)

        item.setData(True, constants.LOADED_ROLE)

    def populate_tree(self):
        if self.root_item is None:
            return
        self.root_notes_item.setFlags(self.root_notes_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.root_notes_item.setData(self.root_course_cat, constants.DIR_ROLE)
        self.root_notes_item.setData(False, constants.LOADED_ROLE)

#        self.root_notes_item.appendRow(QStandardItem("placeholder"))
        self.root_course_item.setFlags(self.root_course_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.root_course_item.setData(True, constants.COURSE_CONTAINER_ROLE)
        self.root_item.appendRow(self.root_notes_item)
        self.root_item.appendRow(self.root_course_item)

        courses = Courses(CONFIG)
        for name, course in courses.courses.items():
            course_item = QStandardItem(name)
            course_item.setFlags(course_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            course_item.setData(True, constants.COURSE_CONTAINER_ROLE)
            self.root_course_item.appendRow(course_item)
            if (main_file := course.typset_files["main"]) is not None:
                main_item = QStandardItem("main")
                main_item.setFlags(main_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                main_item.setData(main_file, constants.FILE_ROLE)
                course_item.appendRow(main_item)
#        if len(courses.courses) == 0:
#            self.root_notes_item.setData(True, constants.EMPTY)

    def connect_toggle_button(self, callback: Callable[[], None]):
        self.minimize_button.clicked.connect(callback)

    def connect_doc_builder(self, builder_widget: QWidget):
        def callback(mode: str) -> None:
            if mode == "Preview":
                builder_widget.setHidden(True)
            else:
                builder_widget.setHidden(False)
        self.mode_selector.connect_mode_btn(callback)


class CollapsedNavBar(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(5, 8, 5, 8)

        self.setFixedWidth(35)
        self.setLayout(self.main_layout)
        self.initUI()

    def initUI(self):
        self.expand_btn = QPushButton()
        self.expand_btn.setStyleSheet(ICON_CSS)
        self.expand_btn.setIcon(QIcon(str(constants.ICON_PATH / "sidebar_right.png")))
        self.expand_btn.setFixedSize(constants.ICON_SIZE)
        self.expand_btn.setToolTip("Open Sidebar")

        self.main_layout.addWidget(self.expand_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.main_layout.addSpacerItem(spacer)

    def connect_toggle_button(self, callback: Callable[[], None]):
        self.expand_btn.clicked.connect(callback)


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
            btn.setFixedHeight(30)
            btn_layout.addWidget(btn)
            self.btn_group.addButton(btn)

        self.btn_preview.setChecked(True)
        btn_widget.setLayout(btn_layout)
        main_layout.addWidget(self.btn_label, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(btn_widget)
        self.setLayout(main_layout)

    def connect_mode_btn(self, callback: Callable[[str], None]):
        self.btn_group.buttonClicked.connect(lambda btn: callback(btn.text()))
