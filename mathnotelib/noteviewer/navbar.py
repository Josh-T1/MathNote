import logging
from typing import Any, Literal, Protocol, Callable, Optional

from PyQt6.QtGui import QBrush, QIcon, QKeyEvent, QMouseEvent, QPalette, QPixmap, QStandardItem, QStandardItemModel, QTransform
from PyQt6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout, QFrame, QGestureEvent, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow, QMenu, QPinchGesture, QPushButton, QRadioButton, QScrollArea, QSizePolicy,
                             QSpacerItem, QStackedWidget, QStyle, QStyleOptionViewItem, QTimeEdit, QToolBar, QTreeView, QVBoxLayout, QWidget)
from PyQt6.QtCore import QByteArray, QDate, QEvent, QFileSystemWatcher, QLine, QModelIndex, QObject, QPoint, QProcess, QSize, QTimer, pyqtBoundSignal, pyqtSignal, Qt


from .style import ICON_CSS, LABEL_CSS, SEARCH_CSS, SWITCH_CSS, TITLE_LABEL_CSS, TREE_VIEW_CSS
from . import constants
from .search import SearchWidget
from ..config import Config, CONFIG
from ..models import SourceFile, Category
from .._enums import FileType
from ..flashcard import FlashcardMainWindow, FlashcardModel, FlashcardController
from ..services import CompilationManager


class StandardItemModel(QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def hasChildren(self, parent: QModelIndex=QModelIndex()) -> bool:
        if parent.isValid() is False or parent.data(constants.LOADED_ROLE) is False:
            return True
        return super().hasChildren(parent)

class NewCourseDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QFormLayout()
        self.setLayout(layout)
        self.name = QLineEdit()

        self.ftype_combo = QComboBox()
        self.weekday_selector = DaysOfWeekSelector()
        self.start_time_edit = QTimeEdit()
        self.end_time_edit = QTimeEdit()
        self.start_date = QDateEdit()
        self.end_date = QDateEdit()
        self.ftype_combo.addItems(["Typst", "LaTeX"])
        self.end_time_edit.setDisplayFormat("HH:mm")
        self.start_time_edit.setDisplayFormat("HH:mm")
        self.start_date.setDisplayFormat("yyyy/MM/dd")
        self.end_date.setDisplayFormat("yyyy/MM/dd")
        layout.addRow("Name:", self.name)
        layout.addRow("File Type:", self.ftype_combo)
        layout.addRow("Weekdays:", self.weekday_selector)
        layout.addRow("Start Time:", self.start_time_edit)
        layout.addRow("End Time:", self.end_time_edit)
        layout.addRow("Start Date:", self.start_date)
        layout.addRow("End Date:", self.end_date)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self) -> tuple[str, FileType, str, str, list[str], str, str]:
        name = self.name.text()
        ftype = FileType.LaTeX if self.ftype_combo.currentText() == "LaTeX" else FileType.Typst
        start_time = self.start_time_edit.time().toString("HH:mm")
        end_time = self.end_time_edit.time().toString("HH:mm")
        weekdays = self.weekday_selector.get_selected_days()
        start_date = self.start_date.date().toString("yyyy/MM/dd")
        end_date = self.end_date.date().toString("yyyy/MM/dd")
        return name, ftype, start_time, end_time, weekdays, start_date, end_date

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


class CourseNavBar(QWidget):
    file_opened = pyqtSignal(SourceFile)
    new_course = pyqtSignal()
    new_lecture = pyqtSignal()
    new_assignment = pyqtSignal()
    delete = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.initUI()

    def root_item(self) -> QStandardItem:
        assert self._root_item is not None
        return self._root_item

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)
        self.setLayout(main_layout)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        #Init widgets
        self.new_lecture_btn = QPushButton()
        self.new_course_btn = QPushButton()
        self.new_assignment_btn = QPushButton()
        self.trash_btn = QPushButton()
        self.model = StandardItemModel()
        self.tree = QTreeView()
        self._root_item = self.model.invisibleRootItem()
        self.menu_bar_layout = QHBoxLayout()
        # Configure
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(lambda p: self.open_menu(p))
        icons = [
                 (self.trash_btn, "trash.png"),
                 (self.new_course_btn, "add_folder.png"),
                 (self.new_lecture_btn, "l.png"),
                 (self.new_assignment_btn, "a.png")
                 ]
        for icon, icon_name in icons:
            icon.setIcon(QIcon(str(constants.ICON_PATH / icon_name)))
            icon.setFixedSize(constants.ICON_SIZE)
            icon.setStyleSheet(ICON_CSS)

        self.tree.setModel(self.model)
        self.tree.setFrameShape(QFrame.Shape.NoFrame)
        self.tree.setStyleSheet(TREE_VIEW_CSS)
        self.tree.clicked.connect(self._item_clicked_callback)
        if (header := self.tree.header()) is not None:
            header.hide()
        self.new_course_btn.setToolTip("New Course")
        self.new_lecture_btn.setToolTip("New Lecture")
        self.trash_btn.setToolTip("Delete")
        self.new_assignment_btn.setToolTip("New Assignment")
        self.new_course_btn.clicked.connect(self.new_course.emit)
        self.new_lecture_btn.clicked.connect(self.new_lecture.emit)
        self.trash_btn.clicked.connect(self.delete.emit)

        # Add to layout
        for btn, _ in icons:
            self.menu_bar_layout.addWidget(btn)
        self.menu_bar_layout.addSpacerItem(QSpacerItem(15, 15, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        main_layout.addLayout(self.menu_bar_layout)
        main_layout.addWidget(self.tree)


    def _toggle_tree(self, idx: QModelIndex) -> None:
        if self.tree.isExpanded(idx):
            self.tree.collapse(idx)
        else:
            self.tree.expand(idx)

    def open_menu(self, p: QPoint):
        pass

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
        elif item.data(constants.COURSE_CONTAINER_ROLE) is not None:
            self._toggle_tree(index)

    def _build_cat_item(self, cat: Category) -> QStandardItem:
        cat_item = QStandardItem(cat.name)
        cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        cat_item.setData(cat, constants.DIR_ROLE)
        cat_item.setData(False, constants.LOADED_ROLE)
        return cat_item

    def _build_file_item(self, file: SourceFile) -> QStandardItem:
        note_item = QStandardItem(file.name)
        note_item.setFlags(note_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        note_item.setData(file, constants.FILE_ROLE)
        return note_item



class NotesNavBar(QWidget):
    file_opened = pyqtSignal(SourceFile)
    new_note = pyqtSignal()
    new_category = pyqtSignal()
    delete = pyqtSignal()
    rename = pyqtSignal()
    load_item = pyqtSignal(QStandardItem, Category)

    def __init__(self):
        super().__init__()
        self.initUI()


    def open_menu(self, p: QPoint):
        idx = self.tree.indexAt(p)
        if not idx.isValid():
            return
        item = self.model.itemFromIndex(idx)
        if item is None:
            return
        #check for course item
        menu = QMenu()
        a1 = menu.addAction("Rename " + item.text())
        if (view := self.tree.viewport()) is not None:
            action = menu.exec(view.mapToGlobal(p))
            if action == a1:
                self.rename.emit()

    def root_item(self) -> QStandardItem:
        assert self._root_item is not None
        return self._root_item

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)
        self.setLayout(main_layout)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        #Init widgets
        self.new_note_btn = QPushButton()
        self.new_category_btn = QPushButton()
        self.trash_btn = QPushButton()
        self.model = StandardItemModel()
        self.tree = QTreeView()
        self._root_item = self.model.invisibleRootItem()

        self.menu_bar_layout = QHBoxLayout()
        #Configure
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(lambda p: self.open_menu(p))
        icons = [
                 (self.trash_btn, "trash.png"),
                 (self.new_category_btn, "add_folder.png"),
                 (self.new_note_btn, "new_note.png")
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
#            header.setText()
        self.model.setHeaderData(0, Qt.Orientation.Horizontal, "Notes")
        self.new_category_btn.setToolTip("New Note Folder")
        self.new_note_btn.setToolTip("New Note")
        self.trash_btn.setToolTip("Delete")
        self.new_category_btn.clicked.connect(self.new_category.emit)
        self.new_note_btn.clicked.connect(self.new_note.emit)
        self.trash_btn.clicked.connect(self.delete.emit)
        # Add to layout
        for btn, _ in icons:
            self.menu_bar_layout.addWidget(btn)
        self.menu_bar_layout.addSpacerItem(QSpacerItem(15, 15, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        main_layout.addLayout(self.menu_bar_layout)
        main_layout.addWidget(self.tree)


    def _expand_callback(self, index: QModelIndex):
        # Remark: the item will originally expand with the placeholder element. Once this occurs
        # we will remove placeholder and populate with correct options.
        item = self.model.itemFromIndex(index)
        if item is None:
            return
        cat = item.data(constants.DIR_ROLE)
        loaded = item.data(constants.LOADED_ROLE)
        if cat is not None and loaded is False:
            self.load_item.emit(item, cat)

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
                self.load_item.emit(item, cat)
            self._toggle_tree(index)


    def _build_cat_item(self, cat: Category) -> QStandardItem:
        cat_item = QStandardItem(cat.name)
        cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        cat_item.setData(cat, constants.DIR_ROLE)
        cat_item.setData(False, constants.LOADED_ROLE)
        return cat_item

    def _build_file_item(self, file: SourceFile) -> QStandardItem:
        note_item = QStandardItem(file.name)
        note_item.setFlags(note_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        note_item.setData(file, constants.FILE_ROLE)
        return note_item

class SettingsWidget(QWidget):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 8, 5, 8)
        main_layout.setSpacing(4)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(main_layout)
        self.setFixedWidth(200)
        self.setLayout(main_layout)
        # Create Widgets
        settings_title = QLabel("Settings")
        root_label = QLabel("Root")
        section_names_label = QLabel("Section Names")
        editor_label = QLabel("Editor")
        log_level_label = QLabel("Log level")
        iterm_2_label = QLabel("Iterm2")
        note_title_label = QLabel("note_title")

        self.log_level_combo = QComboBox()

        self.apply_btn = QPushButton("Apply")
        self.revert_btn = QPushButton("Revert")

        #Configure Widgets
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        self.log_level_combo.addItems(log_levels)


        label_widget = [
                (root_label, QPushButton()),
                (section_names_label, QPushButton()),
                (log_level_label, self.log_level_combo),
                (editor_label, QPushButton()),
                (iterm_2_label, QPushButton()),
                (note_title_label, QPushButton())
                 ]

        settings_title.setStyleSheet(TITLE_LABEL_CSS)

        main_layout.addWidget(settings_title)
        for label, widget in label_widget:
            row_layout = QHBoxLayout()
            label.setStyleSheet(LABEL_CSS)
            label.setFixedHeight(constants.LABEL_HEIGHT)

            row_layout.addWidget(label)
            row_layout.addWidget(widget)
            main_layout.addLayout(row_layout)

        button_row = QHBoxLayout()
        button_row.addWidget(self.revert_btn)
        button_row.addWidget(self.apply_btn)
        main_layout.addLayout(button_row)


#        settings_label = QLabel("Settings")
#        main_layout.addWidget(settings_label, alignment=Qt.AlignmentFlag.AlignTop)

class NavBarContainer(QWidget):
    def __init__(self, notes_navbar: NotesNavBar, courses_navbar: CourseNavBar, settings_widget):
        super().__init__()
        self.tree_visible: bool = True
        self.notes_navbar = notes_navbar
        self.courses_navbar = courses_navbar
        self.settings_widget = settings_widget
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 8, 5, 8)
        main_layout.setSpacing(4)
        self.setLayout(main_layout)
        self.setFixedWidth(200)
        #Init widgets
        self.stack = QStackedWidget()
        self.search_widget = SearchWidget()
        self.minimize_btn = QPushButton()
        self.courses_btn = QPushButton()
        self.notes_btn = QPushButton()
        self.settings_btn = QPushButton()
        self.mode_selector = ModeSelector()
        self.menu_bar_layout = QHBoxLayout()
        self.launcher_widget = LauncherWidget()

        #Configure
        self.settings_btn.setToolTip("Settings")
        self.minimize_btn.setToolTip("Minimize Navbar")
        self.notes_btn.setToolTip("Notes")
        self.courses_btn.setToolTip("Courses")
        self.stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.stack.setContentsMargins(0, 0, 0, 0)
        icons = [
                 (self.minimize_btn, "sidebar_left.png"),
                 (self.settings_btn, "settings_icon.png"),
                 (self.notes_btn, "notes.png"),
                 (self.courses_btn, "school.png"),
                 ]
        for icon, icon_name in icons:
            icon.setIcon(QIcon(str(constants.ICON_PATH / icon_name)))
            icon.setFixedSize(constants.ICON_SIZE)
            icon.setStyleSheet(ICON_CSS)

        self.minimize_btn.setToolTip("Hide Navbar")
        self.notes_btn.setToolTip("Notes")
        self.courses_btn.setToolTip("Courses")
        self.courses_btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.courses_navbar))
        self.notes_btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.notes_navbar))
        self.settings_btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.settings_widget))
        # Add to layout
        for btn in icons:
            self.menu_bar_layout.addWidget(btn[0])
        self.menu_bar_layout.addSpacerItem(QSpacerItem(15, 15, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        main_layout.addLayout(self.menu_bar_layout)
        main_layout.addWidget(self.search_widget)
        main_layout.addWidget(self.stack)
        main_layout.addWidget(self.mode_selector)
        main_layout.addWidget(self.launcher_widget)
        self.stack.addWidget(self.notes_navbar)
        self.stack.addWidget(self.courses_navbar)
        self.stack.addWidget(self.settings_widget)
        self.stack.setCurrentWidget(self.notes_navbar)


#    def set_navbar(self, widget: QWidget):
#        self.stack.setCurrentWidget()

    def connect_toggle_button(self, callback: Callable[[], None]):
        self.minimize_btn.clicked.connect(callback)

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
