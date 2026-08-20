import typing
from PyQt6 import QtGui
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget
from PyQt6.QtCore import Qt

from .navbar import CollapsedNavBar, NavBarContainer
from .style import MAIN_WINDOW_CSS
from .controllers import ViewContainer
from .search import EventFilter
from .constants import VIEWER_WIDTH


class MainWindow(QMainWindow):
    def __init__(self,
                 navbar: NavBarContainer,
                 viewer: ViewContainer,
                 close_callback: None | typing.Callable =None
                 ):
        super().__init__()
        self.navbar_container = navbar
        self.viewer_container = viewer
        self.initUi()
        self._nav_minimal: bool = False
        self._callback = close_callback


    def initUi(self):
        self.navbar_stack = QStackedWidget() # TODO

        self.widget = QWidget()
        self.setCentralWidget(self.widget)

        self.main_layout = QHBoxLayout(self.widget)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 12)

        # Init widgets

        # TODO:  Figure how how to include this with standard navbars..
        self.minimal_nav_bar = CollapsedNavBar()
        # Set controllers. Should this code really live here?

        self.filter = EventFilter(self.navbar_container.search_widget)

        self.installEventFilter(self.filter)
        # Configure
        self.setStyleSheet(MAIN_WINDOW_CSS)
        self.viewer_container.notes_viewer.addTab(focus=True)
        # TODO: I am sure there is a better way
        self.navbar_container.minimize_btn.clicked.connect(lambda: self._toggle_nav_callback())
        self.navbar_container.connect_toggle_button(self._toggle_nav_callback)
        self.minimal_nav_bar.setVisible(False)
        self.setMinimumWidth(
                self.navbar_container.width() + VIEWER_WIDTH + self.minimal_nav_bar.width()
                )
        # Add to layout
        self.main_layout.addWidget(self.navbar_container, alignment=Qt.AlignmentFlag.AlignLeft)
        self.main_layout.addWidget(self.minimal_nav_bar)
        self.main_layout.addWidget(self.viewer_container)

    def _toggle_nav_callback(self):
        self._nav_minimal = not self._nav_minimal
        self.navbar_container.setVisible(not self._nav_minimal)
        self.minimal_nav_bar.setVisible(self._nav_minimal)

    def set_close_callback(self, callback: typing.Callable):
        self._callback = callback

    def closeEvent(self, a0: typing.Optional[QtGui.QCloseEvent]) -> None:
        if self._callback:
            self._callback()
        return super().closeEvent(a0)
