import typing
from PyQt6 import QtGui
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget
from PyQt6.QtCore import Qt

from .navbar import NavbarContainer
from .style import MAIN_WINDOW_CSS
from .controllers import ViewContainer
from .search import EventFilter


class MainWindow(QMainWindow):
    def __init__(self,
                 navbar: NavbarContainer,
                 viewer: ViewContainer,
                 close_callback: None | typing.Callable =None
                 ):
        super().__init__()
        self.navbar_container = navbar
        self.viewer_container = viewer
        self.initUi()
        self._callback = close_callback


    def initUi(self):
        self.navbar_stack = QStackedWidget()

        self.widget = QWidget()
        self.setCentralWidget(self.widget)

        self.main_layout = QHBoxLayout(self.widget)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 12)

#        self.filter = EventFilter(self.navbar_container.search_widget)
#        self.installEventFilter(self.filter)
        # Configure
        self.setStyleSheet(MAIN_WINDOW_CSS)
        self.viewer_container.notes_viewer.addTab(focus=True)
        # Add to layout
        self.main_layout.addWidget(self.navbar_container)
        self.main_layout.addWidget(self.viewer_container)

    def set_close_callback(self, callback: typing.Callable):
        self._callback = callback

    def closeEvent(self, a0: typing.Optional[QtGui.QCloseEvent]) -> None:
        if self._callback:
            self._callback()
        return super().closeEvent(a0)
