import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional, Protocol

from PyQt6.QtGui import QBrush, QTransform
from PyQt6.QtWidgets import (QApplication, QFrame, QGestureEvent, QGraphicsScene, QGraphicsView, QHBoxLayout,
                             QLabel, QListWidget, QMainWindow, QPinchGesture, QToolBar, QTreeView, QVBoxLayout, QWidget)
from PyQt6.QtCore import QEvent, QFileSystemWatcher, QModelIndex, QProcess, QTimer, pyqtSignal, Qt
from PyQt6.QtSvgWidgets import QGraphicsSvgItem, QSvgWidget
from PyQt6 import QtCore

from .navbar import Navbar, CollapsedNavBar, ModeSelector
from .builder_widget import DocumentBuilder
from .viewer import TabbedSvgViewer
from . import constants
from .style import MAIN_WINDOW_CSS
from ..utils import FileType, config, rendered_sorted_key
from ..structure import NotesManager, Courses, Category


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.notes_manager = NotesManager(Path(config["root"]) / "Notes")
        self.widget = QWidget()
        self.main_layout = QHBoxLayout(self.widget)
        self.setCentralWidget(self.widget)
#        self.setContentsMargins(0, 0, 0, 0)
        self.initUi()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(4, 0, 4, 0)
        # TODO
#        self.compile_typst(TYP_FILE_LIVE)
        self.watcher.addPath(constants.TYP_FILE_LIVE)

        self._nav_minimal: bool = False

    def initUi(self):
        self._create_widgets()
        self._configure_widgets()
        self._add_widgets()

    def _create_widgets(self):
        self.toolbar = QToolBar()
        self.watcher = QFileSystemWatcher()
        self.viewer = TabbedSvgViewer()
        self.nav_bar = Navbar(self.update_svg)
        self.minimal_nav_bar = CollapsedNavBar()
        self.doc_builder_widget = DocumentBuilder()

    def _configure_widgets(self):
        self.setStyleSheet(MAIN_WINDOW_CSS)
#        self.viewer.setFixedSize(800, 1000)
        self.viewer.add_svg_tab()
        self.watcher.fileChanged.connect(self.on_typ_changed)
        self.minimal_nav_bar.connect_toggle_button(self._toggle_nav_callback)

        self.nav_bar.connect_toggle_button(self._toggle_nav_callback)
        self.nav_bar.connect_new_note(self._new_note_callback)
        self.nav_bar.connect_new_cat(self._new_cat_callback)
        self.nav_bar.connect_doc_builder(self.doc_builder_widget)

        self.doc_builder_widget.setFixedWidth(200)
        self.doc_builder_widget.setHidden(True)

    def _add_widgets(self):
        self.addToolBar(self.toolbar)
        self.main_layout.addWidget(self.nav_bar, alignment=Qt.AlignmentFlag.AlignLeft)
#        self.main_layout.addWidget(self.minimal_nav_bar, alignment=Qt.AlignmentFlag.AlignLeft)
        self.main_layout.addWidget(self.viewer, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.doc_builder_widget, alignment=Qt.AlignmentFlag.AlignRight)

    def on_typ_changed(self):
        self.watcher.removePath(constants.TYP_FILE_LIVE)
        self.watcher.addPath(constants.TYP_FILE_LIVE)
        self.compile_typst(constants.TYP_FILE_LIVE)

    def compile_typst(self, path: str):
        self.process = QProcess()
        self.process.start("typst", ["compile", path, "--format", "svg"])
        self.process.finished.connect(lambda : self.update_svg(path))

    def update_svg(self, path: str | list[str], tmpdir: Optional[tempfile.TemporaryDirectory] = None):
        paths = path if isinstance(path, list) else [path]
        if all(Path(p).exists() for p in paths):
            self.viewer.load_current_viewer(path, tmpdir=tmpdir)

    def _toggle_nav_callback(self):
        self._nav_minimal = not self._nav_minimal
        if self._nav_minimal:
            self.main_layout.removeWidget(self.nav_bar)
            self.nav_bar.setParent(None)
            self.main_layout.insertWidget(0, self.minimal_nav_bar)
        else:
            self.main_layout.removeWidget(self.minimal_nav_bar)
            self.minimal_nav_bar.setParent(None)
            self.main_layout.insertWidget(0, self.nav_bar)

    def _new_note_callback(self, name: str, cat: Category, note_type: FileType):
#        self.notes_manager.new_note(name,cat, note_type)
        print(name, cat, note_type)

    def _new_cat_callback(self, name: str, cat: Optional[Category] = None):
        print(name, cat)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
