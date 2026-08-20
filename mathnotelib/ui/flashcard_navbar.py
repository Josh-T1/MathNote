import logging
from collections.abc import Callable
from pathlib import Path

from PyQt6.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QLabel, QListView, QMessageBox, QSizePolicy, QSpacerItem, QVBoxLayout,
                             QWidget, QPushButton, QMainWindow, QSpacerItem, QSizePolicy, QScrollArea)
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette, QStandardItem, QStandardItemModel

from ..exceptions import LaTeXCompilationError
from ..config import CONFIG
from ..models import TrackedText
from .._enums import FileType
from .style import BUTTON_CSS, TAB_BTN_EMPTY_CSS



class FlashcardNavBar(QWidget):

    def __init__(self) -> None:
        super().__init__()
        self.initUi()

    def initUi(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)
        self.setLayout(main_layout)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setContentsMargins(0, 0, 0, 0)
        #Init widgets
        self.button_layout = QHBoxLayout()
        self.button_layout.setContentsMargins(0, 0, 0, 0)

        self.course_btn = TabButton("Courses")
        self.deck_btn = TabButton("Deck")


        self.command_bar = CommandBar()

        self.course_btn.btn.clicked.connect(lambda: self.toggle(self.course_btn.label))
        self.deck_btn.btn.clicked.connect(lambda: self.toggle(self.deck_btn.label))

        self.button_layout.addWidget(self.course_btn)
        self.button_layout.addWidget(self.deck_btn)

        self.course_config = FlashcardFromCourseConfigWidget()
        self.deck_config = FlashcardFromDeckConfigWidget()

        main_layout.addLayout(self.button_layout)
        main_layout.addWidget(self.course_config)
        main_layout.addWidget(self.deck_config)
        main_layout.addWidget(self.command_bar)

        self.deck_config.hide()
        self.course_btn.setStyleSheet("background-color: #555;")


    def toggle(self, label: str):
        buttons: dict[str, tuple[QWidget, TabButton]] = {
                "Courses": (self.course_config, self.course_btn),
                "Deck": (self.deck_config, self.deck_btn)
                }
        for (k, v) in buttons.items():
            widget, btn = v
            if k == label:
                btn.setStyleSheet("background-color: #555;")
                widget.show()
            else:
                btn.setStyleSheet("background-color: transparent;")
                widget.hide()


class FlashcardFromDeckConfigWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.initUi()

    def initUi(self):
        self.setContentsMargins(0, 0, 0, 0)
#        self.setFixedWidth(150)

        self.config_layout = QVBoxLayout()
        self.config_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.config_layout)

        self.config_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.config_layout.setSpacing(0)


        # Create widgets
        self.deck_combo_label = QLabel("Deck")
        self.deck_combo_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.deck_combo_label.setContentsMargins(0, 24, 0, 8)
        self.deck_combo= QComboBox()
        self.deck_combo.setContentsMargins(0, 8, 0, 12)
        self.deck_combo.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        section_names = ["definition", "theorem",  "lemma", "proposition", "corollary", "derivation", "All"]
        self.section_list = SectionListWidget(section_names)

        self.config_layout.addWidget(self.deck_combo_label)
        self.config_layout.addWidget(self.deck_combo)
        self.config_layout.addWidget(self.section_list)
        self.config_layout.addStretch()


class FlashcardFromCourseConfigWidget(QWidget):
    update_filters = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.initUi()


    def initUi(self):
        self.setContentsMargins(0, 0, 0, 0)
        self.config_layout = QVBoxLayout()
        self.config_layout.setContentsMargins(0, 0, 0, 0)
        self.config_layout.setSpacing(0)
        self.setLayout(self.config_layout)

        self.course_combo_label = QLabel()
        self.course_combo= QComboBox()
        self.filter_by_lecture_list = QListView()
        # TODO
        self.filter_by_lecture_list.setStyleSheet("""
    QListView {
        border-radius: 6px;
        background: #222;
    }
""")
        self.filter_by_lecture_list_label = QLabel()



        self.random_checkbox_label = QLabel("Randomize")
        self.random_checkbox = QCheckBox()
        self.filter_by_lecture_list_model = QStandardItemModel()

        # Configure
        self.random_checkbox.setChecked(True)
        self.course_combo_label.setText("Select Course")
        self.filter_by_lecture_list_label.setText("Filter by lecture")
        self.filter_by_lecture_list.setModel(self.filter_by_lecture_list_model)
        self.filter_by_lecture_list.setMaximumHeight(150)

        self.course_combo.currentIndexChanged.connect(lambda: self.update_filters.emit())

        section_names = ["definition", "theorem",  "lemma", "proposition", "corollary", "derivation", "All"]
        self.section_list = SectionListWidget(section_names)





        self.course_combo_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.course_combo_label.setContentsMargins(0, 24, 0, 8)
        self.course_combo.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.course_combo.setContentsMargins(0, 8, 0, 12)

        self.filter_by_lecture_list_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.filter_by_lecture_list_label.setContentsMargins(0, 12, 0, 8)
        self.filter_by_lecture_list.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.filter_by_lecture_list.setContentsMargins(0, 8, 0, 12)

        self.random_checkbox_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.random_checkbox_label.setContentsMargins(0, 12, 0, 8)
        self.random_checkbox.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.random_checkbox.setContentsMargins(0, 8, 0, 12)
        # Add widgets
        self.config_layout.addWidget(self.course_combo_label)
        self.config_layout.addWidget(self.course_combo)
        self.config_layout.addWidget(self.section_list)
        self.config_layout.addWidget(self.filter_by_lecture_list_label)
        self.config_layout.addWidget(self.filter_by_lecture_list)
        self.config_layout.addWidget(self.random_checkbox_label)
        self.config_layout.addWidget(self.random_checkbox)




class TabButton(QWidget):

    def __init__(self, label: str):
        super().__init__()
        self.label = label
        self.initUi()

    def initUi(self):
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(QSize(80, 29))
        self.setContentsMargins(0, 0, 0, 0)
        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.btn = QPushButton(self.label)
        self.btn.setFlat(True)
#        self.btn.setFixedWidth(80)
        self.btn.setFlat(True)
        self.btn.setFixedHeight(29)
        self.btn.setStyleSheet(TAB_BTN_EMPTY_CSS)
        main_layout.addWidget(self.btn)
        self.setLayout(main_layout)


class SectionListWidget(QWidget):
    def __init__(self, section_names: list[str]):
        super().__init__()
        self.section_names = section_names

        self.initUi()


    def initUi(self):
        self.setContentsMargins(0, 0, 0, 0)
#        self.setFixedWidth(150)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

        self.section_list_label = QLabel("Select Section")
        self.section_list = QListView()
        # TODO
        self.section_list.setStyleSheet("""
    QListView {
        border-radius: 6px;
        background: #222;
    }
""")

        self.section_list_model = QStandardItemModel()

        for item in self.section_names:
            list_item = QStandardItem(item)
            list_item.setCheckable(True)
            self.section_list_model.appendRow(list_item)
        self.section_list.setModel(self.section_list_model)

        self.section_list.setMaximumHeight(150)
        self.section_list.setContentsMargins(0, 8, 0, 12)
        self.section_list.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.section_list_label.setContentsMargins(0, 12, 0, 8)
        self.section_list_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        main_layout.addWidget(self.section_list_label)
        main_layout.addWidget(self.section_list)



class CommandBar(QWidget):
    def __init__(self):
        super().__init__()
        self.initUi()

    def initUi(self):
        self.setContentsMargins(0, 12, 0, 12)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(main_layout)

        self.create_flashcards_button = QPushButton("Create Flashcards")
        self.create_flashcards_button.setStyleSheet(BUTTON_CSS)
        self.create_flashcards_button.setMaximumWidth(150)
        main_layout.addWidget(self.create_flashcards_button)

