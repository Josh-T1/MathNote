from typing import Literal

from PyQt6.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QLabel, QListView, QSizePolicy, QVBoxLayout,
                             QWidget, QPushButton, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QStandardItem, QStandardItemModel

from .constants import ICON_PATH, ICON_SIZE
from .widgets import TightStackedWidget
from .style import BUTTON_CSS, COLOR_BACKGROUND, COLOR_TAB_UNFOCUSED, COMBO_BOX_CSS, ICON_CSS, LIST_VIEW, TAB_BTN_EMPTY_CSS


class FlashcardNavbar(QWidget):

    def __init__(self) -> None:
        super().__init__()
        self.stack = TightStackedWidget()
        self._prev_name = "course"
        self.initUi()

    def initUi(self):
        main_layout = QVBoxLayout()
        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout()
        self.course_config = FlashcardFromCourseConfigWidget()
        self.deck_config = FlashcardFromDeckConfigWidget()
        self.button_layout = QHBoxLayout()

        self.container_widget.setObjectName("flashcard_navbar_container")

        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.container_layout.setSpacing(4)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.container_widget.setStyleSheet("""
            #flashcard_navbar_container {
                border: 1px solid #555;
                border-radius: 6px;
            }
        """)
        self.container_widget.setFixedHeight(580)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setContentsMargins(0, 0, 0, 0)

        self.container_widget.setLayout(self.container_layout)

        main_layout.setContentsMargins(0, 12, 0, 0)
        main_layout.setSpacing(4)

        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(0)

        self.course_btn = TabButton("Courses")
        self.deck_btn = TabButton("Deck")

        self.create_cards_btn = QPushButton("Create Flashcards")
        self.create_cards_btn.setStyleSheet(BUTTON_CSS)

        self.course_btn.btn.clicked.connect(lambda: self.toggle("course"))
        self.course_btn.setStyleSheet(self._btn_stylesheet("L", True))

        self.deck_btn.btn.clicked.connect(lambda: self.toggle("deck"))
        self.deck_btn.setStyleSheet(self._btn_stylesheet("R", False))

        self.button_layout.addWidget(self.course_btn)
        self.button_layout.addWidget(self.deck_btn)

        self.container_layout.addLayout(self.button_layout)
        self.container_layout.addWidget(self.stack)

        main_layout.addWidget(self.container_widget)
        main_layout.addWidget(self.create_cards_btn)
        main_layout.addStretch()

        self.stack.addWidget(self.course_config)
        self.stack.addWidget(self.deck_config)
        self.stack.setCurrentWidget(self.course_config)

        self.setLayout(main_layout)

    def _btn_stylesheet(self, corner: Literal["L", "R"], focused: bool) -> str:
        color = COLOR_BACKGROUND if focused else COLOR_TAB_UNFOCUSED
        corner_side = "left" if corner == "L" else "right"
        return f"""
        background-color: {color};
        border-top-{corner_side}-radius: 8px;
        border-top: 1px solid #555;
        border-{corner_side}: 1px solid #555;
        """

    def toggle(self, name: Literal["course", "deck"]):
        if (name == "course" and self._prev_name == "course") or (name == "deck" and self._prev_name == "deck"):
            return
        self._prev_name = name
        if self.stack.currentWidget() == self.course_config:
            self.course_btn.setStyleSheet(self._btn_stylesheet("L", False))
            self.deck_btn.setStyleSheet(self._btn_stylesheet("R", True))
            self.stack.setCurrentWidget(self.deck_config)
        else:
            self.deck_btn.setStyleSheet(self._btn_stylesheet("R", False))
            self.course_btn.setStyleSheet(self._btn_stylesheet("L", True))
            self.stack.setCurrentWidget(self.course_config)

class FlashcardFromDeckConfigWidget(QWidget):
    new_deck = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.initUi()

    def initUi(self):
        random_layout = QHBoxLayout()
        self.config_layout = QVBoxLayout()
        self.section_list = SectionListWidget()
        self.random_checkbox = QCheckBox()
        self.filter_by_lecture_list_model = QStandardItemModel()
        self.random_checkbox_label = QLabel("Shuffle")
        self.deck_btn_bar_layout = QHBoxLayout()
        self.deck_combo_label = QLabel("Select Deck")
        self.deck_combo = QComboBox()
        self.new_deck_btn = QPushButton()
        self.trash_btn = QPushButton()
        self.rename_btn = QPushButton()

        self.setContentsMargins(8, 0, 8, 0)

        self.config_layout.setContentsMargins(0, 0, 0, 0)
        self.config_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.config_layout.setSpacing(0)

        random_layout.setContentsMargins(0, 12, 0, 0)
        random_layout.setSpacing(12)
        random_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.random_checkbox.setChecked(False)

        self.section_list.setStyleSheet(LIST_VIEW)

        self.deck_btn_bar_layout.setContentsMargins(0, 8, 0, 8)
        self.deck_btn_bar_layout.setSpacing(4)
        self.deck_btn_bar_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)


        self.deck_combo_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.deck_combo_label.setContentsMargins(0, 12, 0, 0)

        self.deck_combo.setStyleSheet(COMBO_BOX_CSS)
        self.deck_combo.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        self.new_deck_btn.setIcon(QIcon(str(ICON_PATH / "add.png")))
        self.new_deck_btn.setFixedSize(ICON_SIZE)
        self.new_deck_btn.setStyleSheet(ICON_CSS)

        self.trash_btn.setIcon(QIcon(str(ICON_PATH / "trash.png")))
        self.trash_btn.setFixedSize(ICON_SIZE)
        self.trash_btn.setStyleSheet(ICON_CSS)

        self.rename_btn.setIcon(QIcon(str(ICON_PATH / "edit.png")))
        self.rename_btn.setFixedSize(ICON_SIZE)
        self.rename_btn.setStyleSheet(ICON_CSS)

        random_layout.addWidget(self.random_checkbox_label)
        random_layout.addWidget(self.random_checkbox)

        self.deck_btn_bar_layout.addWidget(self.trash_btn)
        self.deck_btn_bar_layout.addWidget(self.rename_btn)
        self.deck_btn_bar_layout.addWidget(self.new_deck_btn)

        self.config_layout.addWidget(self.deck_combo_label)
        self.config_layout.addLayout(self.deck_btn_bar_layout)
        self.config_layout.addWidget(self.deck_combo)
        self.config_layout.addWidget(self.section_list)
        self.config_layout.addLayout(random_layout)

        self.setLayout(self.config_layout)


class FlashcardFromCourseConfigWidget(QWidget):
    update_filters = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.initUi()

    def initUi(self):
        self.setContentsMargins(8, 0, 8, 0)
        self.config_layout = QVBoxLayout()
        self.config_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.config_layout.setContentsMargins(0, 0, 0, 0)
        self.config_layout.setSpacing(0)
        self.setLayout(self.config_layout)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.course_combo_label = QLabel()
        self.course_combo= QComboBox()
        self.course_combo.setStyleSheet(COMBO_BOX_CSS)
        self.filter_by_lecture_list = QListView()
        self.filter_by_lecture_list.setStyleSheet(LIST_VIEW)
        self.filter_by_lecture_list_label = QLabel()

        random_widget = QWidget()
        random_layout = QHBoxLayout()
        random_widget.setLayout(random_layout)
        random_layout.setContentsMargins(0, 12, 0, 0)
        random_layout.setSpacing(12)
        random_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.random_checkbox_label = QLabel("Shuffle")
        self.random_checkbox = QCheckBox()
        self.filter_by_lecture_list_model = QStandardItemModel()

        # Configure
        self.random_checkbox.setChecked(False)
        self.course_combo_label.setText("Select Course")
        self.filter_by_lecture_list_label.setText("Filter by lecture")
        self.filter_by_lecture_list.setModel(self.filter_by_lecture_list_model)
        self.filter_by_lecture_list.setMaximumHeight(200)

        self.course_combo.currentIndexChanged.connect(lambda: self.update_filters.emit())

        self.section_list = SectionListWidget()
        self.section_list.setFixedHeight(200)
        self.course_combo_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.course_combo_label.setContentsMargins(0, 12, 0, 8)
        self.course_combo.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.course_combo.setContentsMargins(0, 8, 0, 12)

        self.filter_by_lecture_list_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.filter_by_lecture_list_label.setContentsMargins(0, 12, 0, 8)
        self.filter_by_lecture_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.filter_by_lecture_list.setContentsMargins(0, 8, 0, 12)

        # Add widgets
        self.config_layout.addWidget(self.course_combo_label)
        self.config_layout.addWidget(self.course_combo)
        self.config_layout.addWidget(self.section_list)
        self.config_layout.addWidget(self.filter_by_lecture_list_label)
        self.config_layout.addWidget(self.filter_by_lecture_list)

        random_layout.addWidget(self.random_checkbox_label)
        random_layout.addWidget(self.random_checkbox)
        self.config_layout.addWidget(random_widget)

class TabButton(QWidget):

    def __init__(self, label: str):
        super().__init__()
        self.label = label
        self.initUi()

    def initUi(self):
        main_layout = QHBoxLayout()
        self.btn = QPushButton(self.label)

        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.btn.setFlat(True)
        self.btn.setFlat(True)
        self.btn.setFixedHeight(29)
        self.btn.setStyleSheet(TAB_BTN_EMPTY_CSS)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setContentsMargins(0, 0, 0, 0)

        main_layout.addWidget(self.btn)
        self.setLayout(main_layout)


class SectionListWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUi()

    def initUi(self):
        main_layout = QVBoxLayout()

        self.section_list_label = QLabel("Select Section")
        self.section_list = QListView()
        self.section_list_model = QStandardItemModel()

        self.section_list.setStyleSheet(LIST_VIEW)
        self.section_list.setModel(self.section_list_model)

        self.section_list.setContentsMargins(0, 8, 0, 12)
        self.section_list.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.section_list_label.setContentsMargins(0, 12, 0, 8)
        self.section_list_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(self.section_list_label)
        main_layout.addWidget(self.section_list)

    def add_items(self, items: list[str]):
        self.section_list_model.clear()
        for item in items:
            list_item = QStandardItem(item)
            list_item.setCheckable(True)
            self.section_list_model.appendRow(list_item)


class CommandBar(QWidget):
    def __init__(self):
        super().__init__()
        self.initUi()

    def initUi(self):
        self.setContentsMargins(0, 24, 0, 24)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(main_layout)

        self.create_flashcards_button = QPushButton("Create Flashcards")
        self.create_flashcards_button.setStyleSheet(BUTTON_CSS)
        main_layout.addWidget(self.create_flashcards_button)
