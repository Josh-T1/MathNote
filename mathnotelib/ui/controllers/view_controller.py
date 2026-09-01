from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QWidget

from ..widgets import TightStackedWidget
from ..navbar import NavbarContainer
from ..file_viewer import TabbedSvgViewer
from ..flashcard_viewer import FlashcardView



class ViewContainer(QWidget):

    def __init__(self, notes_viewer: TabbedSvgViewer, flashcard_viewer: FlashcardView):
        super().__init__()
        self.notes_viewer = notes_viewer
        self.flashcard_viewer = flashcard_viewer
        self.view_stack = TightStackedWidget()
        self.initUi()

    def initUi(self):
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        self.view_stack.addWidget(self.notes_viewer)
        self.view_stack.addWidget(self.flashcard_viewer)
        self.view_stack.setCurrentWidget(self.notes_viewer)
        self.main_layout.addWidget(self.view_stack)


class ViewController(QObject):
    def __init__(self, window: QMainWindow, navbar_container: NavbarContainer, view_container: ViewContainer):
        super().__init__()
        self.window = window
        self.navbar_cont = navbar_container
        self.window_cont = view_container
        self.connect_handlers()

    def connect_handlers(self):
        self.navbar_cont.notes_btn.clicked.connect(lambda: self.set_notes_view())
        self.navbar_cont.courses_btn.clicked.connect(lambda: self.set_course_notes_view())
        self.navbar_cont.flashcards_btn.clicked.connect(lambda: self.set_flashcard_view())
        self.navbar_cont.minimize_btn.clicked.connect(lambda: self.toggle_navbar_container())
        self.navbar_cont.collapsed_widget.expand_btn.clicked.connect(lambda: self.toggle_navbar_container())
        self.navbar_cont.settings_btn.clicked.connect(lambda: self.set_settings_view())

    def set_settings_view(self):
        self.navbar_cont.stack.setCurrentWidget(self.navbar_cont.settings_navbar)

    def toggle_navbar_container(self):
        diff = self.navbar_cont.visible_widget.width() - self.navbar_cont.collapsed_widget.width()
        current_width = self.window.width()
        current_height = self.window.height()

        if self.navbar_cont.container_stack.currentWidget() == self.navbar_cont.collapsed_widget:
            self.navbar_cont.container_stack.setCurrentWidget(self.navbar_cont.visible_widget)
            self.window.setMinimumWidth(1050)

        else:
            self.navbar_cont.container_stack.setCurrentWidget(self.navbar_cont.collapsed_widget)
            self.window.setMinimumWidth(current_width - diff)
            self.window.resize(current_width - diff, current_height)

    def set_flashcard_view(self):
        self.navbar_cont.stack.setCurrentWidget(self.navbar_cont.flashcard_navbar)
        self.window_cont.view_stack.setCurrentWidget(self.window_cont.flashcard_viewer)
        self.window.setFixedSize(1050, 860)

    def set_notes_view(self):
        self.navbar_cont.stack.setCurrentWidget(self.navbar_cont.notes_navbar)
        self.window_cont.view_stack.setCurrentWidget(self.window_cont.notes_viewer)
        self.window.setMinimumSize(1050, 1000)
        self.window.setMaximumSize(16777215, 16777215)

    def set_course_notes_view(self):
        self.navbar_cont.stack.setCurrentWidget(self.navbar_cont.courses_navbar)
        self.window_cont.view_stack.setCurrentWidget(self.window_cont.notes_viewer)
        self.window.setMinimumSize(1050, 1000)
        self.window.setMaximumSize(16777215, 16777215)  # Qt's default max











