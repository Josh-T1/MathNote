from PyQt6.QtGui import QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import (QApplication, QFrame, QGestureEvent, QGraphicsScene, QGraphicsView, QHBoxLayout,
                             QLabel, QListWidget, QMainWindow, QPinchGesture, QStackedWidget, QToolBar, QTreeView, QVBoxLayout, QWidget)
from PyQt6.QtCore import QEvent, QFileSystemWatcher, QModelIndex, QObject, QProcess, QTimer, pyqtSignal, Qt
from PyQt6.QtSvgWidgets import QGraphicsSvgItem, QSvgWidget


from .navbar import CollapsedNavBar, CourseNavBar, NavBarContainer, NotesNavBar, SettingsNavBar
from .builder_widget import DocumentBuilder
from .svg_viewer import TabbedSvgViewer, ZMultiPageViewer
from .flashcard_navbar import FlashcardNavBar
from .style import MAIN_WINDOW_CSS
from .controllers import LiveTypstController, NoteController, CourseController, ViewContainer, ViewController
from .search import SearchWidget
from ..config import CONFIG
from .._enums import FileType

from .constants import VIEWER_HEIGHT, VIEWER_WIDTH
from mathnotelib.ui import constants

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



# Get controllers tf out of here
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUi()
        self._nav_minimal: bool = False

    def initUi(self):
        self.navbar_stack = QStackedWidget() # TODO

        self.widget = QWidget()
        self.setCentralWidget(self.widget)

        self.main_layout = QHBoxLayout(self.widget)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 12)

        # Init widgets
        self.notes_view = TabbedSvgViewer()
        self.flashcard_view = ZMultiPageViewer()
        self.flashcard_view.setMinimumSize(constants.VIEWER_WIDTH, constants.VIEWER_HEIGHT)
        self.view_container = ViewContainer(self.notes_view, self.flashcard_view)

        self.minimal_nav_bar = CollapsedNavBar()
        # Set controllers. Should this code really live here?
        notes_navbar = NotesNavBar()
        courses_navbar = CourseNavBar()
        flashcards_navbar = FlashcardNavBar()
        settings = SettingsNavBar(CONFIG)

        self.notes_controller = NoteController(self, notes_navbar, self.notes_view)
        self.coures_controller = CourseController(self, courses_navbar, self.notes_view)
        self.preview_controller = LiveTypstController(self, self.notes_view)

        self.navbar_cont = NavBarContainer(notes_navbar, courses_navbar, flashcards_navbar, settings)

        self.view_controller = ViewController(self.navbar_cont, self.view_container)

        self.filter = EventFilter(self.navbar_cont.search_widget)

        self.installEventFilter(self.filter)
        # Configure
        self.setStyleSheet(MAIN_WINDOW_CSS)
        self.notes_view.setMinimumSize(VIEWER_WIDTH, VIEWER_HEIGHT)
        self.notes_view.addTab(focus=True)
        # TODO: I am sure there is a better way
        self.minimal_nav_bar.connect_toggle_button(self._toggle_nav_callback)
        self.navbar_cont.connect_toggle_button(self._toggle_nav_callback)
        self.minimal_nav_bar.setVisible(False)
        self.setMinimumWidth(
                self.navbar_cont.width() + VIEWER_WIDTH + self.minimal_nav_bar.width()
                )
        # Add to layout
        self.main_layout.addWidget(self.navbar_cont, alignment=Qt.AlignmentFlag.AlignLeft)
        self.main_layout.addWidget(self.minimal_nav_bar)
        self.main_layout.addWidget(self.view_container)

    def _toggle_nav_callback(self):
        self._nav_minimal = not self._nav_minimal
        self.navbar_cont.setVisible(not self._nav_minimal)
        self.minimal_nav_bar.setVisible(self._nav_minimal)



