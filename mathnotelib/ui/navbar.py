from typing import Callable
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                             QSpacerItem, QStackedWidget, QVBoxLayout, QWidget)
from PyQt6.QtCore import Qt

from .style import BUTTON_CSS, COMBO_BOX_CSS, ICON_CSS, LABEL_CSS, TITLE_LABEL_CSS
from .widgets import TightStackedWidget
from . import constants
from .file_navbar import NotesNavbar, CourseNavbar
from .flashcard_navbar import FlashcardNavbar
from ..config import Config


# this needs note repositories
class SettingsNavbar(QWidget):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 12, 0, 0)
        main_layout.setSpacing(12)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(main_layout)
        self.setLayout(main_layout)
        # Create Widgets
        settings_title = QLabel("Settings")
        root_label = QLabel("Root")
        section_names_label = QLabel("Section Names")
        log_level_label = QLabel("Log level")
        self.log_level_combo = QComboBox()

        self.save = QPushButton("Save")

        self.save.setStyleSheet(BUTTON_CSS)

        #Configure Widgets
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        self.log_level_combo.addItems(log_levels)


        label_widget = [
                (root_label, QComboBox()),
                (section_names_label, QComboBox()),
                (log_level_label, self.log_level_combo),
                 ]

        settings_title.setStyleSheet(TITLE_LABEL_CSS)

        main_layout.addWidget(settings_title)
        for label, widget in label_widget:
            row_layout = QHBoxLayout()
            label.setStyleSheet(LABEL_CSS)
            label.setFixedHeight(constants.LABEL_HEIGHT)

            if isinstance(widget, QComboBox):
                widget.setStyleSheet(COMBO_BOX_CSS)

            row_layout.addWidget(label)
            row_layout.addWidget(widget)
            main_layout.addLayout(row_layout)

        button_row = QHBoxLayout()
        button_row.addWidget(self.save)
        main_layout.addLayout(button_row)


#        settings_label = QLabel("Settings")
#        main_layout.addWidget(settings_label, alignment=Qt.AlignmentFlag.AlignTop)


class NavbarContainer(QWidget):

    def __init__(self,
                 notes_navbar: NotesNavbar,
                 courses_navbar: CourseNavbar,
                 flashcard_navbar: FlashcardNavbar,
                 settings_navbar: SettingsNavbar,
                 ):
        super().__init__()
        self.container_stack = TightStackedWidget()
        self.tree_visible: bool = True
        self.notes_navbar = notes_navbar
        self.courses_navbar = courses_navbar
        self.settings_navbar = settings_navbar
        self.flashcard_navbar = flashcard_navbar
        self.stack = QStackedWidget()
        self.initUI()

    def initUI(self):
        self.visible_widget = QWidget()
        self.collapsed_widget = CollapsedNavbarContainer()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        visible_layout = QVBoxLayout()
        visible_layout.setContentsMargins(5, 8, 5, 8)
        visible_layout.setSpacing(4)
        visible_layout.setContentsMargins(5, 8, 5, 8)
        visible_layout.setSpacing(4)

        self.visible_widget.setLayout(visible_layout)
        self.visible_widget.setFixedWidth(250)

        self.courses_btn = QPushButton()
        self.notes_btn = QPushButton()
        self.settings_btn = QPushButton()
        self.flashcards_btn = QPushButton()
        self.menu_bar_layout = QHBoxLayout()
        self.minimize_btn = QPushButton()

        #Configure
        self.settings_btn.setToolTip("Settings")
        self.minimize_btn.setToolTip("Minimize Navbar")
        self.notes_btn.setToolTip("Notes")
        self.courses_btn.setToolTip("Courses")
        self.flashcards_btn.setToolTip("Flashcards")

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


        # Add to layout
        for btn in icons:
            self.menu_bar_layout.addWidget(btn[0])
        self.menu_bar_layout.addSpacerItem(QSpacerItem(15, 15, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        visible_layout.addLayout(self.menu_bar_layout)
        visible_layout.addWidget(self.stack)
        self.stack.setFixedWidth(240)
#        collapsed_layout.addWidget(self.collapsed_container)

        self.stack.addWidget(self.notes_navbar)
        self.stack.addWidget(self.courses_navbar)
        self.stack.addWidget(self.flashcard_navbar)
        self.stack.addWidget(self.settings_navbar)
        self.stack.setCurrentWidget(self.notes_navbar)

        self.container_stack.addWidget(self.visible_widget)
        self.container_stack.addWidget(self.collapsed_widget)
        self.container_stack.setCurrentWidget(self.visible_widget)

        main_layout.addWidget(self.container_stack)
        self.setLayout(main_layout)





class CollapsedNavbarContainer(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(5, 8, 5, 8)

        self.setFixedWidth(35)
        self.setLayout(self.main_layout)
        self.expand_btn = QPushButton()
        self.initUI()

    def initUI(self):
        self.expand_btn.setStyleSheet(ICON_CSS)
        self.expand_btn.setIcon(QIcon(str(constants.ICON_PATH / "sidebar_right.png")))
        self.expand_btn.setFixedSize(constants.ICON_SIZE)
        self.expand_btn.setToolTip("Open Sidebar")

        self.main_layout.addWidget(self.expand_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.main_layout.addSpacerItem(spacer)

    def connect_toggle_button(self, callback: Callable[[], None]):
        self.expand_btn.clicked.connect(callback)




