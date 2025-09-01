from PyQt6.QtGui import QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import (QApplication, QFrame, QGestureEvent, QGraphicsScene, QGraphicsView, QHBoxLayout,
                             QLabel, QListWidget, QMainWindow, QPinchGesture, QToolBar, QTreeView, QVBoxLayout, QWidget)
from PyQt6.QtCore import QEvent, QFileSystemWatcher, QModelIndex, QObject, QProcess, QTimer, pyqtSignal, Qt
from PyQt6.QtSvgWidgets import QGraphicsSvgItem, QSvgWidget

from .navbar import CollapsedNavBar, CourseNavBar, ModeSelector, NavBarContainer, NotesNavBar, SettingsWidget
from .builder_widget import DocumentBuilder
from .viewer import TabbedSvgViewer
from .style import MAIN_WINDOW_CSS
from .controllers import NoteController, CourseController
from .search import SearchWidget
from ..config import CONFIG
from .._enums import FileType

class EventFilter(QObject):
    def __init__(self, search_widget: SearchWidget):
        super().__init__()
        self.search_widget = search_widget
        self.search_results = self.search_widget.results
        self.search_input = self.search_widget.input

    def eventFilter(self, a0: QObject | None, a1: QEvent | None) -> bool:
        if a0 is None or a1 is None:
            return super().eventFilter(a0, a1)
        if isinstance(a1, QMouseEvent) and a1.type() == QEvent.Type.MouseButtonPress:
            global_pos = a1.globalPosition().toPoint()
            if not self.search_input.geometry().contains(self.search_input.mapFromGlobal(global_pos)):
                self.search_results.hide()
                self.search_input.clear()
                self.search_input.clearFocus()

        if a0 is self.search_input and a1.type() == QEvent.Type.FocusOut:
            self.search_results.hide()

        if a1.type() == QEvent.Type.KeyPress and isinstance(a1, QKeyEvent):
            if a1.key() == Qt.Key.Key_Escape:
                self.search_results.hide()
                self.search_input.clear()
                self.search_input.clearFocus()

        return super().eventFilter(a0, a1)

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
        self.minimal_nav_bar = CollapsedNavBar()
        self.doc_builder_widget = DocumentBuilder()
        # Set controllers. Should this code really live here?
        notes_navbar = NotesNavBar()
        courses_navbar = CourseNavBar()
        settings = SettingsWidget(CONFIG)
        self.notes_controller = NoteController(self, notes_navbar, self.viewer)
        self.coures_controller = CourseController(self, courses_navbar, self.viewer)
        self.navbar = NavBarContainer(notes_navbar, courses_navbar, settings)
        self.filter = EventFilter(self.navbar.search_widget)
        self.installEventFilter(self.filter)
        # Configure
        self.setStyleSheet(MAIN_WINDOW_CSS)
#        self.viewer.setFixedSize(800, 1000)
        self.viewer.add_svg_tab()
        self.minimal_nav_bar.connect_toggle_button(self._toggle_nav_callback)
        self.navbar.connect_toggle_button(self._toggle_nav_callback)
        self.doc_builder_widget.setFixedWidth(200)
        self.doc_builder_widget.setHidden(True)
        self.minimal_nav_bar.setVisible(False)
        # Add to layout
        self.main_layout.addWidget(self.navbar, alignment=Qt.AlignmentFlag.AlignLeft)
        self.main_layout.addWidget(self.minimal_nav_bar)
        self.main_layout.addWidget(self.viewer, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.doc_builder_widget, alignment=Qt.AlignmentFlag.AlignRight)

    def _toggle_nav_callback(self):
        self._nav_minimal = not self._nav_minimal
        self.navbar.setVisible(not self._nav_minimal)
        self.minimal_nav_bar.setVisible(self._nav_minimal)
