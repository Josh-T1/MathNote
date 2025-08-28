import sys
import tempfile
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (QApplication, QFrame, QGestureEvent, QGraphicsScene, QGraphicsView, QHBoxLayout,
                             QLabel, QListWidget, QMainWindow, QPinchGesture, QToolBar, QTreeView, QVBoxLayout, QWidget)
from PyQt6.QtCore import QEvent, QFileSystemWatcher, QModelIndex, QProcess, QTimer, pyqtSignal, Qt
from PyQt6.QtSvgWidgets import QGraphicsSvgItem, QSvgWidget

from mathnotelib.structure.courses import Courses

from . import constants
from .navbar import Navbar, CollapsedNavBar, ModeSelector
from .builder_widget import DocumentBuilder
from .viewer import TabbedSvgViewer
from .style import MAIN_WINDOW_CSS

from ..utils import FileType, CONFIG
from ..structure import NotesManager, Courses, Category


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUi()
#        self.compile_typst(TYP_FILE_LIVE)
        self._nav_minimal: bool = False

    def initUi(self):
        self.widget = QWidget()
        self.main_layout = QHBoxLayout(self.widget)
        self.setCentralWidget(self.widget)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        # Init widgets
        self.viewer = TabbedSvgViewer()
        self.nav_bar = Navbar()
        self.minimal_nav_bar = CollapsedNavBar()
        self.doc_builder_widget = DocumentBuilder()
        # Configure
        self.setStyleSheet(MAIN_WINDOW_CSS)
#        self.viewer.setFixedSize(800, 1000)
        self.viewer.add_svg_tab()
        self.minimal_nav_bar.connect_toggle_button(self._toggle_nav_callback)
        self.nav_bar.connect_toggle_button(self._toggle_nav_callback)
        self.doc_builder_widget.setFixedWidth(200)
        self.doc_builder_widget.setHidden(True)
        # Add to layout
        self.main_layout.addWidget(self.nav_bar, alignment=Qt.AlignmentFlag.AlignLeft)
        self.main_layout.addWidget(self.minimal_nav_bar)
        self.minimal_nav_bar.setVisible(False)
#        self.main_layout.addWidget(self.minimal_nav_bar, alignment=Qt.AlignmentFlag.AlignLeft)
        self.main_layout.addWidget(self.viewer, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.doc_builder_widget, alignment=Qt.AlignmentFlag.AlignRight)

    def _toggle_nav_callback(self):
        self._nav_minimal = not self._nav_minimal
        self.nav_bar.setVisible(not self._nav_minimal)
        self.minimal_nav_bar.setVisible(self._nav_minimal)
