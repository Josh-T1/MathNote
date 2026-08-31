from pathlib import Path
from PyQt6.QtGui import QIcon, QStandardItemModel
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy,
                             QSpacerItem, QStackedWidget, QTreeView, QVBoxLayout, QWidget)
from PyQt6.QtCore import QSize, Qt, pyqtSignal

from .style import BOXED_LABEL_CSS, BUTTON_CSS, COLOR_FOCUSED, COMBO_BOX_CSS, ICON_CSS, LABEL_CSS, TITLE_LABEL_CSS, TREE_VIEW_CSS
from .widgets import PathLabel, TightStackedWidget
from .constants import ICON_PATH, LABEL_HEIGHT, ICON_SIZE
from .file_navbar import NotesNavbar, CourseNavbar
from .flashcard_navbar import FlashcardNavbar
from ..config import Config

def make_styled_label(text: str = "", boxed = False) -> QLabel:
    label = QLabel(text)
    if boxed:
        label.setStyleSheet(BOXED_LABEL_CSS)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    else:
        label.setStyleSheet(LABEL_CSS)
    label.setFixedHeight(LABEL_HEIGHT)
    return label

def make_row_layout(left: int = 0, top: int = 0, right: int = 0, bottom: int = 0, spacing=8) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.setContentsMargins(left, top, right, bottom)
    layout.setSpacing(spacing)
    layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
    return layout


def make_icon_btn(icon_name: str) -> QPushButton:
    btn = QPushButton()
    btn.setIcon(QIcon(str(ICON_PATH / f"{icon_name}.png")))
    btn.setFixedSize(ICON_SIZE)
    btn.setStyleSheet(ICON_CSS)
    return btn

# this needs note repositories
class SettingsNavbar(QWidget):
    pattern_changed = pyqtSignal(object, str, str)
    new_section = pyqtSignal()
    delete_section = pyqtSignal()
    experimental_export = pyqtSignal(bool)

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.initUI()

    def initUI(self):
        # Create layouts/Widgets
        main_layout = QVBoxLayout()
        root_layout = make_row_layout()
        btn_layout = make_row_layout(top=4)
        log_layout = make_row_layout()
        export_layout = make_row_layout()
        config_dir_layout = make_row_layout(top=4)

        note_pkg_layout = make_row_layout(top=4)
        pkg_combo_layout = make_row_layout(left=8)
        latex_pkg_layout = make_row_layout(left=8)
        typst_macro_layout = make_row_layout(left=8)
        latex_macro_layout = make_row_layout(left=8, bottom=24)

        self.root_label = make_styled_label("Root path")
        self.config_dir_label = make_styled_label("Config path")
        self.root_val= PathLabel()
        self.config_dir_val = PathLabel()
        self.section_names_label = QLabel("Sections")
        self.section_view = QTreeView()
        self.section_model = QStandardItemModel()
        self.log_level_label = make_styled_label("Log level")
        self.log_level_combo = QComboBox()
        self.settings_title = QLabel("General Settings")
        self.flashcards_settings_title = QLabel("Flashcard Settings")
        self.note_settings_title = QLabel("Note Settings")
        self.export_checkbox = QCheckBox()
        self.latex_preamble_path_val = PathLabel()
        self.latex_macro_path_val = PathLabel()
        self.typst_preamble_path_val = PathLabel()
        self.typst_macro_path_val = PathLabel()

#        self.typst_pkg_combo = QComboBox()

        self.new_pkg_btn = make_icon_btn("add")
        self.del_pkg_btn = make_icon_btn("trash")
        self.trash_btn = make_icon_btn("trash")
        self.new_btn = make_icon_btn("add")

        self.save_btn = QPushButton("Save")

        #Configure
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.new_btn.clicked.connect(self.new_section.emit)
        self.trash_btn.clicked.connect(self.delete_section.emit)
        self.export_checkbox.clicked.connect(lambda t: self.experimental_export.emit(t))


        # TODO controller should populate combo using config
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        self.settings_title.setStyleSheet(TITLE_LABEL_CSS)
        self.flashcards_settings_title.setStyleSheet(TITLE_LABEL_CSS)
        self.note_settings_title.setStyleSheet(TITLE_LABEL_CSS)
        self.flashcards_settings_title.setContentsMargins(0, 24, 0, 0)
        self.note_settings_title.setContentsMargins(0, 24, 0, 0)

        self.log_level_combo.addItems(log_levels)
        self.log_level_combo.setStyleSheet(COMBO_BOX_CSS)

#        self.root_val.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
#        self.root_val.setStyleSheet(BOXED_LABEL_CSS)
#        self.root_val.setFixedHeight(LABEL_HEIGHT)
#
#        self.config_dir_val.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
#        self.config_dir_val.setStyleSheet(BOXED_LABEL_CSS)
#        self.config_dir_val.setFixedHeight(LABEL_HEIGHT)

#        self.typst_pkg_combo.setStyleSheet(COMBO_BOX_CSS)
#        self.typst_pkg_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.section_names_label.setStyleSheet(LABEL_CSS)
        self.section_view.setStyleSheet(TREE_VIEW_CSS)
        self.section_view.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.section_view.setMinimumHeight(200)
        self.section_model.setColumnCount(2)
        self.section_view.setMaximumHeight(600)
        self.section_view.setModel(self.section_model)
        self.section_view.setIndentation(10)
        self.section_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        if (header := self.section_view.header()) is not None: header.hide()

        self.save_btn.setStyleSheet(BUTTON_CSS)

        root_layout.addWidget(self.root_label)
        root_layout.addWidget(self.root_val)

        config_dir_layout.addWidget(self.config_dir_label)
        config_dir_layout.addWidget(self.config_dir_val)

        btn_layout.addWidget(self.section_names_label)
        btn_layout.addWidget(self.trash_btn)
        btn_layout.addWidget(self.new_btn)

        log_layout.addWidget(self.log_level_label)
        log_layout.addStretch()
        log_layout.addWidget(self.log_level_combo)

        note_pkg_layout.addWidget(make_styled_label("Preamble Paths"))
#        note_pkg_layout.addWidget(self.del_pkg_btn)
#        note_pkg_layout.addWidget(self.new_pkg_btn)

        pkg_combo_layout.addWidget(make_styled_label("Typst"))
        pkg_combo_layout.addWidget(self.typst_preamble_path_val)

        latex_pkg_layout.addWidget(make_styled_label("LaTeX"))
        latex_pkg_layout.addWidget(self.latex_preamble_path_val)

        typst_macro_layout.addWidget(make_styled_label("Typst"))
        typst_macro_layout.addWidget(self.typst_macro_path_val)
        latex_macro_layout.addWidget(make_styled_label("LaTeX"))
        latex_macro_layout.addWidget(self.latex_macro_path_val)

        export_layout.addWidget(make_styled_label("Enable Experimental Export"))
        export_layout.addStretch()
        export_layout.addWidget(self.export_checkbox)

        main_layout.addWidget(self.settings_title)
        main_layout.addLayout(root_layout)
        main_layout.addLayout(config_dir_layout)
        main_layout.addLayout(log_layout)
        main_layout.addLayout(export_layout)

        main_layout.addWidget(self.flashcards_settings_title)
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(self.section_view)

        main_layout.addWidget(self.note_settings_title)
        main_layout.addLayout(note_pkg_layout)
        main_layout.addLayout(pkg_combo_layout)
        main_layout.addLayout(latex_pkg_layout)
        main_layout.addWidget(make_styled_label("Macro Paths"))
        main_layout.addLayout(typst_macro_layout)
        main_layout.addLayout(latex_macro_layout)
        main_layout.addWidget(self.save_btn)

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
            btn.setIcon(QIcon(str(ICON_PATH / btn_name)))
            btn.setFixedSize(ICON_SIZE)
            btn.setStyleSheet(ICON_CSS)
            self.menu_bar_layout.addWidget(btn)

        self.minimize_btn.setToolTip("Hide Navbar")
        self.notes_btn.setToolTip("Notes")
        self.courses_btn.setToolTip("Courses")

#        self.menu_bar.setContentsMargins(0, 0, 0, 0)
#        self.menu_bar.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.menu_bar_layout.addSpacerItem(QSpacerItem(15, 15, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        self.menu_bar_layout.setContentsMargins(0, 0, 0, 8)
        self.menu_bar_layout.setSpacing(4)

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
        self.expand_btn.setIcon(QIcon(str(ICON_PATH / "sidebar_right.png")))
        self.expand_btn.setFixedSize(ICON_SIZE)
        self.expand_btn.setToolTip("Open Sidebar")

        self.main_layout.addWidget(self.expand_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self.main_layout.addSpacerItem(spacer)

        self.setFixedWidth(35)
        self.setLayout(self.main_layout)
