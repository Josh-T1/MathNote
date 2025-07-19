import sys
import tempfile
from typing import Callable, Optional
from PyQt6.QtGui import QMouseEvent, QPalette, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QMainWindow, QPushButton, QSizePolicy,
                             QSpacerItem, QStyle, QStyleOptionViewItem, QToolBar, QTreeView, QVBoxLayout, QWidget)
from PyQt6.QtCore import QFileSystemWatcher, QModelIndex, QProcess, pyqtSignal, Qt
from PyQt6.QtSvgWidgets import QSvgWidget
from mathnotelib.note.note import Category, Note, OutputFormat
from .style import SVG_VIEWER_CSS, TOGGLE_BUTTON_CSS, TREE_VIEW_CSS
from mathnotelib.course.courses import Course, Courses
from ..utils import NoteType, config
from ..note import NotesManager
from pathlib import Path

ROOT_DIR = Path(config["root"])

OUTPUT_FILE_NAME = "rendered.svg"
TYP_FILE_LIVE = "/tmp/live.typ"
SVG_FILE_LIVE = "/tmp/live.svg"

FILE_ROLE = Qt.ItemDataRole.UserRole + 1
DIR_ROLE = Qt.ItemDataRole.UserRole + 2
LOADED_ROLE = Qt.ItemDataRole.UserRole + 3

class Navbar(QWidget):
    file_opened = pyqtSignal(str)

    def __init__(self, callback: Callable[[str], None]):
        """
        callback: callable with str argument, should be a valid typst path
        """
        super().__init__()
        self.tree_visible: bool = True
        self.update_svg_func = callback

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)
        self.setFixedWidth(200)

        self.initUI()

    def initUI(self):
        self._create_widgets()
        self._add_widgets()

        self.populate_tree()

    def _create_widgets(self):
        palette = QPalette()

        self.toggle_button = QPushButton("x")
        self.menu_bar_layout = QHBoxLayout()
        self.toggle_button.setStyleSheet(TOGGLE_BUTTON_CSS)
        self.toggle_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.toggle_button.clicked.connect(self.toggle_tree)
        self.model = QStandardItemModel()
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setPalette(palette)
        self.tree.setFrameShape(QFrame.Shape.NoFrame)
        self.tree.header().hide() #TODO: don't think header() every returns none..
        self.root_item = self.model.invisibleRootItem()
        self.tree.expanded.connect(self._carrot_clicked)
        self.tree.setStyleSheet(TREE_VIEW_CSS)
        self.tree.clicked.connect(self._on_item_clicked)

    def _carrot_clicked(self, index: QModelIndex):
        # Remark: the item will originally expand with the placeholder element. Once this occurs
        # we will remove placeholder and populate with correct options. This could give rise to a bug where placeholder persists
        item = self.model.itemFromIndex(index)
        if item is None:
            return
        cat = item.data(DIR_ROLE)
        loaded = item.data(LOADED_ROLE)
        if cat is not None and loaded is not None:
            if loaded is False:
                self._load_item(item, cat)

    def _add_widgets(self):
        self.menu_bar_layout.addWidget(self.toggle_button)
#        self.hidden_layout.setFixedWidth(40)
        self.menu_bar_layout.addSpacerItem(QSpacerItem(15, 15, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        self.main_layout.addLayout(self.menu_bar_layout)
        self.main_layout.addWidget(self.tree)

    # How do I deal with courses?
    def _on_item_clicked(self, index: QModelIndex):
        item = self.model.itemFromIndex(index)
        if item is None:
            return

        # TODO: handle failed compilation
        if item.data(FILE_ROLE) is not None:
            note: Note = item.data(FILE_ROLE)

            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                rendered_path = tmpdir_path / OUTPUT_FILE_NAME
                code = note.compile(OutputFormat.SVG, tmpdir_path, OUTPUT_FILE_NAME)
                self.update_svg_func(str(rendered_path))

        # For any item with this role we must do 2 things:
        #   1. Check to see if we should expand or collapse tree around item
        #   2. Check if subcategories and notes have been load. If not, load data and populate rows.
        elif item.data(DIR_ROLE):
            loaded = item.data(LOADED_ROLE)

            if loaded is False:
                cat: Category = item.data(DIR_ROLE)
                self._load_item(item, cat)

            if self.tree.isExpanded(index):
                self.tree.collapse(index)
            else:
                self.tree.expand(index)

    def _load_item(self, item: QStandardItem, cat: Category):
                # Check for placeholder row
        if (c1 := item.child(0)):
            if c1.text() == "placeholder":
                item.removeRow(0)

        for sub_cat in cat.children():
            sub_cat_item = QStandardItem(sub_cat.name)
            sub_cat_item.setData(sub_cat, DIR_ROLE)
            sub_cat_item.setData(False, LOADED_ROLE)
            sub_cat_item.appendRow(QStandardItem("placeholder"))

            item.appendRow(sub_cat_item)

        for note in cat.notes():
            note_item = QStandardItem(note.name)
            note_item.setData(note, FILE_ROLE)
            item.appendRow(note_item)

        item.setData(True, LOADED_ROLE)

    def populate_tree(self):
        notes_dir = ROOT_DIR / "Notes"
        root_cat = NotesManager.build_root_category(notes_dir)
        courses = Courses(config)

        root_notes_item = QStandardItem(root_cat.name)
        root_notes_item.setData(root_cat, DIR_ROLE)
        root_notes_item.setData(False, LOADED_ROLE)
        root_notes_item.appendRow(QStandardItem("placeholder"))
        self.root_item.appendRow(root_notes_item)

    def toggle_tree(self):
        self.tree_visible = not self.tree_visible
#        self.tree.setVisible(self.tree_visible)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.widget = QWidget()
        self.main_layout = QHBoxLayout(self.widget)
        self.setCentralWidget(self.widget)
        self.setContentsMargins(0, 0, 0, 0)
        self.initUi()

        # TODO
        self.compile_typst(TYP_FILE_LIVE)
        self.watcher.addPath(TYP_FILE_LIVE)

    def initUi(self):
        self.setStyleSheet("QMainWindow { background-color: #2E2E2E; }")
        self._create_widgets()
        self._add_widgets()

    def _create_widgets(self):
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)
        self.viewer = QSvgWidget()
        self.viewer.setStyleSheet(SVG_VIEWER_CSS)
        self.viewer.setFixedSize(800, 1000)
        self.watcher = QFileSystemWatcher()
        self.watcher.fileChanged.connect(self.on_typ_changed)

        self.nav_bar = Navbar(self.update_svg)

    def _add_widgets(self):
        self.main_layout.addWidget(self.nav_bar)
        self.main_layout.addWidget(self.viewer)

    def on_typ_changed(self):
        self.watcher.removePath(TYP_FILE_LIVE)
        self.watcher.addPath(TYP_FILE_LIVE)
        self.compile_typst(TYP_FILE_LIVE)

    def render_note(self, path: str):
        pass

    def compile_typst(self, path: str):
        self.process = QProcess()
        self.process.start("typst", ["compile", path, "--format", "svg"])
        self.process.finished.connect(lambda : self.update_svg(path))

    def update_svg(self, path: str):
        if Path(path).exists():
            self.viewer.load(path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
