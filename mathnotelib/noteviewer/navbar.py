from PyQt6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                             QSpacerItem, QStackedWidget, QVBoxLayout, QWidget)
from PyQt6.QtCore import Qt

from .style import ICON_CSS, LABEL_CSS, TITLE_LABEL_CSS
from . import constants
from .search import SearchWidget
from .file_navbar import NotesNavBar, CourseNavBar
from ..config import Config


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
        self.setFixedWidth(250)
        #Init widgets
        self.stack = QStackedWidget()
        self.search_widget = SearchWidget()
        self.minimize_btn = QPushButton()
        self.courses_btn = QPushButton()
        self.notes_btn = QPushButton()
        self.settings_btn = QPushButton()
        self.flashcards_btn = QPushButton()
        self.menu_bar_layout = QHBoxLayout()


        #Configure
        self.settings_btn.setToolTip("Settings")
        self.minimize_btn.setToolTip("Minimize Navbar")
        self.notes_btn.setToolTip("Notes")
        self.courses_btn.setToolTip("Courses")
        self.flashcards_btn.setToolTip("Flashcards")

        self.stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.stack.setContentsMargins(0, 0, 0, 0)
        icons = [
                 (self.minimize_btn, "sidebar_left.png"),
                 (self.settings_btn, "settings_icon.png"),
                 (self.notes_btn, "notes.png"),
                 (self.courses_btn, "school.png"),
                 (self.flashcards_btn, "cards.png")
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
        self.flashcards_btn.clicked.connect(lambda: print(''))

        # Add to layout
        for btn in icons:
            self.menu_bar_layout.addWidget(btn[0])
        self.menu_bar_layout.addSpacerItem(QSpacerItem(15, 15, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        main_layout.addLayout(self.menu_bar_layout)
        main_layout.addWidget(self.search_widget)
        main_layout.addWidget(self.stack)
        self.stack.addWidget(self.notes_navbar)
        self.stack.addWidget(self.courses_navbar)
        self.stack.addWidget(self.settings_widget)
        self.stack.setCurrentWidget(self.notes_navbar)


#    def set_navbar(self, widget: QWidget):
#        self.stack.setCurrentWidget()

    def connect_toggle_button(self, callback: Callable[[], None]):
        self.minimize_btn.clicked.connect(callback)

#    def connect_doc_builder(self, builder_widget: QWidget):
#        def callback(mode: str) -> None:
#            if mode == "Preview":
#                builder_widget.setHidden(True)
#            else:
#                builder_widget.setHidden(False)
#        self.mode_selector.connect_mode_btn(callback)


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

