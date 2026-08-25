from typing import Callable
from PyQt6.QtGui import QIcon, QStandardItemModel
from PyQt6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                             QSpacerItem, QStackedWidget, QTreeView, QVBoxLayout, QWidget)
from PyQt6.QtCore import Qt

from .style import BOXED_LABEL_CSS, BUTTON_CSS, COLOR_FOCUSED, COMBO_BOX_CSS, ICON_CSS, LABEL_CSS, TITLE_LABEL_CSS, TREE_VIEW_CSS
from .widgets import PathLabel, TightStackedWidget
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
        # Create layouts/Widgets
        main_layout = QVBoxLayout()
        ##Label
        self.root_label = QLabel("Root")
        self.root_val= PathLabel()
        self.section_names_label = QLabel("Section Names")
        self.section_view = QTreeView()
        self.section_model = QStandardItemModel()
        self.log_level_label = QLabel("Log level")
        self.log_level_combo = QComboBox()
        self.settings_title = QLabel("Settings")
        ##Btn
        self.save_btn = QPushButton("Save")


        #Configure
        main_layout.setContentsMargins(0, 12, 0, 0)
        main_layout.setSpacing(12)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


        self.settings_title.setStyleSheet(TITLE_LABEL_CSS)

        self.log_level_combo.addItems(log_levels)
        self.log_level_combo.setStyleSheet(COMBO_BOX_CSS)

        self.root_label.setStyleSheet(LABEL_CSS)
        self.root_label.setFixedHeight(constants.LABEL_HEIGHT)

        self.root_val.setStyleSheet(BOXED_LABEL_CSS)
        self.root_val.setFixedHeight(constants.LABEL_HEIGHT)

        self.section_names_label.setStyleSheet(LABEL_CSS)
        self.section_view.setStyleSheet(TREE_VIEW_CSS)
        self.section_view.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.section_view.setMinimumHeight(200)
        self.section_view.setMaximumHeight(600)
        self.section_view.setModel(self.section_model)
        if (header := self.section_view.header()) is not None: header.hide()

        self.save_btn.setStyleSheet(BUTTON_CSS)

        rows = [
                [self.settings_title],
                [self.root_label, self.root_val],
                [self.section_names_label],
                [self.section_view],
                [self.log_level_label, self.log_level_combo],
                [self.save_btn]
                ]
        for row in rows:
            row_layout = QHBoxLayout()
            for widget in row:
                row_layout.addWidget(widget)
            main_layout.addLayout(row_layout)

        self.setLayout(main_layout)


class NavbarContainer(QWidget):

    def __init__(
            self,
            notes_navbar: NotesNavbar,
            courses_navbar: CourseNavbar,
            flashcard_navbar: FlashcardNavbar,
            settings_navbar: SettingsNavbar
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
        main_layout = QVBoxLayout()
        visible_layout = QVBoxLayout()

        self.visible_widget = QWidget()
        self.collapsed_widget = CollapsedNavbarContainer()

        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

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
        self.menu_bar = QWidget()
        self.minimize_btn = QPushButton()

        #Configure
        self.settings_btn.setToolTip("Settings")
        self.minimize_btn.setToolTip("Minimize Navbar")
        self.notes_btn.setToolTip("Notes")
        self.courses_btn.setToolTip("Courses")
        self.flashcards_btn.setToolTip("Flashcards")

        self.stack.setFixedWidth(240)
        self.stack.setContentsMargins(0, 0, 0, 0)

        icons = [
                 (self.minimize_btn, "sidebar_left.png"),
                 (self.settings_btn, "settings_icon.png"),
                 (self.notes_btn, "notes.png"),
                 (self.courses_btn, "school.png"),
                 (self.flashcards_btn, "cards.png")
                 ]
        for btn, btn_name in icons:
            btn.setIcon(QIcon(str(constants.ICON_PATH / btn_name)))
            btn.setFixedSize(constants.ICON_SIZE)
            btn.setStyleSheet(ICON_CSS)
            self.menu_bar_layout.addWidget(btn)

        self.minimize_btn.setToolTip("Hide Navbar")
        self.notes_btn.setToolTip("Notes")
        self.courses_btn.setToolTip("Courses")

#        self.menu_bar.setContentsMargins(0, 0, 0, 0)
#        self.menu_bar.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.menu_bar_layout.addSpacerItem(QSpacerItem(15, 15, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        self.menu_bar_layout.setContentsMargins(0, 0, 0, 8)
        self.menu_bar_layout.setSpacing(2)

        self.menu_bar.setStyleSheet(f"""
            QWidget {{
                border-bottom: 1px solid {COLOR_FOCUSED};
            }}

            """)

        self.menu_bar.setLayout(self.menu_bar_layout)

        visible_layout.addWidget(self.menu_bar)
        visible_layout.addWidget(self.stack)


        self.stack.addWidget(self.notes_navbar)
        self.stack.setCurrentWidget(self.notes_navbar)
        self.stack.addWidget(self.courses_navbar)
        self.stack.addWidget(self.flashcard_navbar)
        self.stack.addWidget(self.settings_navbar)


        self.container_stack.addWidget(self.visible_widget)
        self.container_stack.addWidget(self.collapsed_widget)
        self.container_stack.setCurrentWidget(self.visible_widget)

        main_layout.addWidget(self.container_stack)
        self.setLayout(main_layout)


class CollapsedNavbarContainer(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.initUI()

    def initUI(self):
        self.main_layout = QVBoxLayout()

        self.expand_btn = QPushButton()
        spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.main_layout.setContentsMargins(5, 8, 5, 8)

        self.expand_btn.setStyleSheet(ICON_CSS)
        self.expand_btn.setIcon(QIcon(str(constants.ICON_PATH / "sidebar_right.png")))
        self.expand_btn.setFixedSize(constants.ICON_SIZE)
        self.expand_btn.setToolTip("Open Sidebar")

        self.main_layout.addWidget(self.expand_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self.main_layout.addSpacerItem(spacer)

        self.setFixedWidth(35)
        self.setLayout(self.main_layout)
