from typing import Optional

from PyQt6.QtGui import QIcon, QStandardItem
from PyQt6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QMenu, QPushButton, QSizePolicy,
                             QSpacerItem, QTreeView, QVBoxLayout, QWidget)
from PyQt6.QtCore import  QModelIndex, QPoint, pyqtSignal, Qt


from .style import ICON_CSS, LABEL_CSS, TITLE_LABEL_CSS, TREE_VIEW_CSS
from .constants import FILE_ROLE, COURSE_CONTAINER_ROLE, COURSE_DIR, LOADED_ROLE, DIR_ROLE, ICON_PATH, ICON_SIZE
from ..models import SourceFile, Category
from .widgets import StandardItemModel

class BaseFileNavbar(QWidget):
    file_opened = pyqtSignal(SourceFile)
    load_item = pyqtSignal(QStandardItem, Category)

    def __init__(self):
        super().__init__()
        self.model = StandardItemModel()
        self.tree = QTreeView()
        self.tree.setIndentation(10)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
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
        if (file := item.data(FILE_ROLE)) is not None:
            assert isinstance(file, SourceFile)
            self.file_opened.emit(file)
        # For any item with this role we must do 2 things:
        #   1. Check to see if we should expand or collapse tree around item
        #   2. Check if subcategories and notes have been load. If not, load data and populate rows.
        elif item.data(COURSE_CONTAINER_ROLE) is not None or item.data(COURSE_DIR) is not None:
            self._toggle_tree(index)

        elif (cat := item.data(DIR_ROLE)) is not None:
            assert isinstance(cat, Category)
            loaded = item.data(LOADED_ROLE)
            if loaded is False:
                self.load_item.emit(item, cat)
            self._toggle_tree(index)

    def _get_item_and_index(self) -> tuple[Optional[QStandardItem], Optional[QModelIndex]]:
        idx = self.tree.currentIndex()
        if not idx.isValid(): #TODO error msg for top level
            return None, None
        item = self.model.itemFromIndex(idx)
        return item, idx

    def _build_cat_item(self, cat: Category) -> QStandardItem:
        func = getattr(cat, "pretty_name", lambda: cat.name)
        cat_item = QStandardItem(func())
        flags = cat_item.flags()
        flags &= ~Qt.ItemFlag.ItemIsEditable
        flags |= Qt.ItemFlag.ItemIsDropEnabled
        flags |= Qt.ItemFlag.ItemIsDragEnabled
        cat_item.setFlags(flags)
        cat_item.setData(cat, DIR_ROLE)
        cat_item.setData(False, LOADED_ROLE)
        return cat_item

    def _build_file_item(self, file: SourceFile) -> QStandardItem:
        func = getattr(file, "pretty_name", lambda: file.name)
        note_item = QStandardItem(func())
        flags = note_item.flags()
        flags &= ~Qt.ItemFlag.ItemIsEditable
        flags &= ~Qt.ItemFlag.ItemIsDropEnabled
        flags |= Qt.ItemFlag.ItemIsDragEnabled
        note_item.setFlags(flags)
        note_item.setData(file, FILE_ROLE)
        note_item.setToolTip(func())
        return note_item


class CourseNavbar(BaseFileNavbar):
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
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
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
            icon.setIcon(QIcon(str(ICON_PATH / icon_name)))
            icon.setFixedSize(ICON_SIZE)
            icon.setStyleSheet(ICON_CSS)

        self.tree.setModel(self.model)
        self.tree.setFrameShape(QFrame.Shape.NoFrame)
        self.tree.setStyleSheet(TREE_VIEW_CSS)
        self.tree.clicked.connect(self._item_clicked_callback)
        if (header := self.tree.header()) is not None:
            header.hide()
        self.tree.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.tree.setMinimumHeight(250)

        self.new_course_btn.setToolTip("New Course")
        self.new_lecture_btn.setToolTip("New Lecture")
        self.trash_btn.setToolTip("Delete")
        self.new_assignment_btn.setToolTip("New Assignment")

        self.new_assignment_btn.clicked.connect(self.new_assignment.emit)
        self.new_course_btn.clicked.connect(self.new_course.emit)
        self.new_lecture_btn.clicked.connect(self.new_lecture.emit)
        self.trash_btn.clicked.connect(self.delete.emit)

        # Add to layout
        for btn, _ in icons:
            self.menu_bar_layout.addWidget(btn)
        self.menu_bar_layout.addSpacerItem(QSpacerItem(15, 15, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        main_layout.addLayout(self.menu_bar_layout)
        main_layout.addWidget(self.tree)


class NotesNavbar(BaseFileNavbar):
    new_note = pyqtSignal()
    new_category = pyqtSignal()
    delete = pyqtSignal()
    rename = pyqtSignal()
    move_item = pyqtSignal(dict, QModelIndex)

    def __init__(self):
        super().__init__()
        self.initUI()
        self.model.move_signal = self.move_item
#        self.tree.setAcceptDrops(True)
#        self.tree.setDropIndicatorShown(True)


    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)
        self.setLayout(main_layout)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
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
            icon.setIcon(QIcon(str(ICON_PATH / icon_name)))
            icon.setFixedSize(ICON_SIZE)
            icon.setStyleSheet(ICON_CSS)

        self.tree.setModel(self.model)
        self.tree.setFrameShape(QFrame.Shape.NoFrame)
        self.tree.expanded.connect(self._expand_callback)
        self.tree.setStyleSheet(TREE_VIEW_CSS)
        self.tree.clicked.connect(self._item_clicked_callback)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDefaultDropAction(Qt.DropAction.MoveAction)

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
        cat = item.data(DIR_ROLE)
        loaded = item.data(LOADED_ROLE)
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





