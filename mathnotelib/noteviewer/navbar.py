from typing import Callable

from PyQt6.QtGui import QIcon, QStandardItem
from PyQt6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QSizePolicy,
                             QSpacerItem, QStackedWidget, QTreeView, QVBoxLayout, QWidget)
from PyQt6.QtCore import  QModelIndex, QPoint, pyqtSignal, Qt

from .style import ICON_CSS, LABEL_CSS, SEARCH_CSS, SWITCH_CSS, TITLE_LABEL_CSS, TREE_VIEW_CSS
from . import constants
from .search import SearchWidget
from ..config import Config
from ..models import SourceFile, Category
from .ui_components import StandardItemModel, LauncherWidget, ModeSelector


class BaseNavBar(QWidget):
    file_opened = pyqtSignal(SourceFile)
    load_item = pyqtSignal(QStandardItem, Category)

    def __init__(self):
        super().__init__()
        self.model = StandardItemModel()
        self.tree = QTreeView()
        self._root_item = self.model.invisibleRootItem()

    def root_item(self) -> QStandardItem:
        assert self._root_item is not None
        return self._root_item

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
        elif item.data(constants.COURSE_CONTAINER_ROLE) is not None:
            self._toggle_tree(index)

        elif item.data(constants.DIR_ROLE) is not None:
            loaded = item.data(constants.LOADED_ROLE)
            if loaded is False:
                cat: Category = item.data(constants.DIR_ROLE)
                self.load_item.emit(item, cat)
            self._toggle_tree(index)

    def _get_item_and_index(self) -> tuple[QStandardItem | None, None | QModelIndex]:
        idx = self.tree.currentIndex()
        if not idx.isValid(): #TODO error msg for top level
            return None, None
        item = self.model.itemFromIndex(idx)
        return item, idx


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


class CourseNavBar(BaseNavBar):
    new_course = pyqtSignal()
    new_lecture = pyqtSignal()
    new_assignment = pyqtSignal()
    delete = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.initUI()

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
        self.menu_bar_layout = QHBoxLayout()
        # Configure
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
#        self.tree.customContextMenuRequested.connect(lambda p: self.open_menu(p))
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


class NotesNavBar(BaseNavBar):
    new_note = pyqtSignal()
    new_category = pyqtSignal()
    delete = pyqtSignal()
    rename = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.initUI()

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
        self.new_category_btn.setToolTip("New Category")
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


class SettingsNavBar(QWidget):
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
