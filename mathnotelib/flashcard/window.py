import math
import logging
from collections.abc import Callable

from PyQt6.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QLabel, QListView, QMessageBox, QSizePolicy, QSpacerItem, QVBoxLayout,
                             QWidget, QPushButton, QMainWindow, QSpacerItem, QSizePolicy, QScrollArea)
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor, QPalette, QStandardItem, QStandardItemModel

from ..exceptions import LaTeXCompilationError
from ..config import CONFIG
from ..models import Course
from ..services import CourseRepository

logger = logging.getLogger("mathnote")

ZOOM_FACTOR = 3


class InfoButton(QWidget):
    clicked = pyqtSignal()

    def __init__(self, diameter=16):
        super().__init__()
        self.info_button_layout = QVBoxLayout()
        self.info_button_layout.setContentsMargins(0, 0, 0, 0)
        self.info_button_layout.setSpacing(0)
        self.diameter = diameter
        self.radius = self.diameter // 2
        self.initUI()
        self.setLayout(self.info_button_layout)

    def initUI(self):
        self.info_button = QPushButton("?")

        self.info_button.setFixedSize(self.diameter, self.diameter)
        self.info_button.setStyleSheet(f"border-radius: {self.radius}px; background-color: grey; font-weight: bold;")
        self.info_button.clicked.connect(self.clicked.emit)

        self.info_button_layout.addWidget(self.info_button)

    def set_message(self, msg: str):
        msg_box = QMessageBox(self)
        msg_box.setText(msg)
        msg_box.exec()

    def connect(self, slot):
        self.clicked.connect(slot)


# TODO remove courses
class VConfigBar(QWidget):
    update_filters = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.initUi()



    def initUi(self):
        self.config_layout = QVBoxLayout()
        self.setFixedWidth(160)
        self.setLayout(self.config_layout)
        # Create Widgets
        self.course_combo_label = QLabel()
        self.course_combo= QComboBox()
        self.section_list = QListView()
        self.filter_by_week_list = QListView()
        self.filter_by_week_list_label = QLabel()
        self.section_list_label = QLabel()
        self.create_flashcards_button = QPushButton("Create Flashcards")
        self.open_main = QPushButton("Open main")
        self.random_checkbox_label = QLabel("Randomize")
        self.random_checkbox = QCheckBox()
        self.filter_by_week_list_model = QStandardItemModel()
        self.section_list_model = QStandardItemModel()

        # Add iterm2 widgets if enabled
        if CONFIG.iterm2_enabled:
            self.launch_iterm_button = QPushButton("Launch iterm")
            self.config_layout.addWidget(self.launch_iterm_button)

        # Configure
        self.random_checkbox.setChecked(True)
        self.course_combo_label.setText("Select Course")
        self.section_list_label.setText("Select Section")
        self.filter_by_week_list_label.setText("Filter by week")
        self.filter_by_week_list.setModel(self.filter_by_week_list_model)
        self.filter_by_week_list.setMaximumWidth(125)
        self.filter_by_week_list.setMaximumHeight(150)

        self.course_combo.currentIndexChanged.connect(lambda: self.update_filters.emit())

        self.section_list_items = ["definition", "theorem",  "lemma", "proposition",
                                   "corollary", "derivation", "All"]
        for item in self.section_list_items:
            list_item = QStandardItem(item)
            list_item.setCheckable(True)
            self.section_list_model.appendRow(list_item)
        self.section_list.setModel(self.section_list_model)

        self.section_list.setMaximumWidth(125)
        self.section_list.setMaximumHeight(150)
        self.create_flashcards_button.setMaximumWidth(150)
        self.course_combo.setMaximumWidth(150)

        # Add widgets
        self.config_layout.addWidget(self.course_combo_label)
        self.config_layout.addWidget(self.course_combo)
        self.config_layout.addWidget(self.section_list_label)
        self.config_layout.addWidget(self.section_list)
        self.config_layout.addWidget(self.filter_by_week_list_label)
        self.config_layout.addWidget(self.filter_by_week_list)
        self.config_layout.addWidget(self.random_checkbox_label)
        self.config_layout.addWidget(self.random_checkbox)
        self.config_layout.addWidget(self.create_flashcards_button)
        self.config_layout.addWidget(self.open_main)

        self.config_layout.addStretch()



class HButtonBar(QWidget):
    def __init__(self):
        super().__init__()
        self.initUi()


    def initUi(self):
        self.bar_layout = QHBoxLayout()
        self.setLayout(self.bar_layout)
        self.setFixedHeight(50)

        # Create widgets
        self.next_flashcard_button = QPushButton("Next", self)
        self.prev_flashcard_button = QPushButton("Prev", self)
        self.show_answer_button = QPushButton("Show Answer", self)
        self.show_question_button = QPushButton("Show Question", self)
        self.show_proof_button = QPushButton("Show Proof", self)

        # Configure widgets
        self.show_proof_button.setHidden(True)
        self.prev_flashcard_button.setFixedSize(75, 30)
        self.next_flashcard_button.setFixedSize(75, 30)

        # Add widgets
        self.bar_layout.addStretch()
        self.bar_layout.addWidget(self.prev_flashcard_button)
        self.bar_layout.addWidget(self.next_flashcard_button)
        self.bar_layout.addStretch()
        self.bar_layout.addWidget(self.show_question_button)
        self.bar_layout.addWidget(self.show_answer_button)
        self.bar_layout.addWidget(self.show_proof_button)
        self.bar_layout.addStretch()
        self.bar_layout.addStretch()

    def connect_clicked_show_question_button(self, func):
        self.show_question_button.clicked.connect(func)

    def connect_clicked_show_answer_button(self, func):
        self.show_answer_button.clicked.connect(func)

    def connect_clicked_next_button(self, func):
        self.next_flashcard_button.clicked.connect(func)

    def connect_clicked_prev_button(self, func):
        self.prev_flashcard_button.clicked.connect(func)

class HBar(QWidget):
    def __init__(self):
        super().__init__()
        self.initUi()


    def initUi(self):
        self.bar_layout = QHBoxLayout()
        self.bar_layout.setContentsMargins(5, 0, 5, 0)
        self.setFixedHeight(16)
        self.setLayout(self.bar_layout)

        # Create widgets
        self.info_button = InfoButton(diameter=16)
        self.flashcard_type = QLabel()

        # Configure widgets
        self.flashcard_type.setStyleSheet("font-size: 18px; color: white; font-family: Arial")

        # Add widgets
        self.bar_layout.addWidget(self.info_button)
        self.bar_layout.addStretch()
        self.bar_layout.addWidget(self.flashcard_type)
        self.bar_layout.addStretch()
        self.bar_layout.addStretch()

    def connect_clicked_info_button(self, callback):
        self.info_button.connect(callback)


class PdfWindow(QWidget):
    def __init__(self, widget):
        super().__init__()
        self.parent_widget = widget
        self.initUi()



    def initUi(self):
        self.pdf_layout = QHBoxLayout()
        self.setLayout(self.pdf_layout)

        # Create widgets
        self.scroll_area = QScrollArea(self.parent_widget)
        self.pdf_viewer = QPdfView(self.scroll_area)
        self._palette = QPalette()

        # Configure widgets
        self._palette.setBrush(QPalette.ColorRole.Dark, QColor('white'))
        self.pdf_viewer.setPalette(self._palette)
        # Setting pdf_viewer parent to scroll_area allows QPdfView scroll bar. Setting hidden=True hides scroll_area box used to scroll gui window
        self.scroll_area.setHidden(True)

        # Add widgets
        self.pdf_layout.addWidget(self.pdf_viewer)

    def _load_pdf(self, pdf_path: str, tex: str) -> QPdfDocument.Error:
        """ Loads pdf into pdf_viewer and set viewer settings
        -- Params --
        pdf_path: (str) absolute path to pdf
        returns: QPdfDocument.Error
        """
        if pdf_path is None:
            return QPdfDocument.Error.FileNotFound

        pdf_document = QPdfDocument(self)
        load_status = pdf_document.load(pdf_path)

        if load_status == QPdfDocument.Error.None_:
            self.document = pdf_path
            self.pdf_viewer.setDocument(pdf_document)
            if len(tex) > 100:
                self.pdf_viewer.setZoomMode(QPdfView.ZoomMode.FitToWidth)
            else:
                self.pdf_viewer.setZoomMode(QPdfView.ZoomMode.Custom)
                self.pdf_viewer.setZoomFactor(ZOOM_FACTOR)
        return load_status

    # TODO
    def plot_tex(self, pdf_path: str, tex: str):
        """
        -- Params --
        pdf_path: absolute path to pdf
        return: load status
        """
#        target = card.pdf_question_path if question else card.pdf_answer_path # I dont like this. Plot tex should only take in filepath?
        load_status = self._load_pdf(pdf_path, tex)
        if load_status != QPdfDocument.Error.None_:
            self.document = None
            raise LaTeXCompilationError(f"Failed to compile card: {pdf_path}. Load status: {load_status}")

# Yeah... idk about all those one methods
class FlashcardMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.close_callback = None
        self.initUi()

    def initUi(self):
        self.widget = QWidget()
        self.main_layout = QHBoxLayout(self.widget)
        self.main_flashcard_layout = QVBoxLayout()
        self.resize(1000, 600)
        self.setMinimumSize(400, 300)
        self.setCentralWidget(self.widget)

        # Create widgets
        self.flashcard_button_bar = HButtonBar()
        self.top_bar = HBar()
        self.pdf_window = PdfWindow(self.widget)
        self.config_bar = VConfigBar()
        spacer = QSpacerItem(40, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        # Add widgets
        self.main_flashcard_layout.addWidget(self.top_bar)
        self.main_flashcard_layout.addWidget(self.pdf_window, 3)
        self.main_flashcard_layout.addWidget(self.flashcard_button_bar)

        self.main_layout.addItem(spacer)
        self.main_layout.addLayout(self.main_flashcard_layout)
        self.main_layout.addWidget(self.config_bar)

    @property
    def document(self):
        return self.pdf_window.document

    def closeEvent(self, a0):
        """a0 is an event. Why the name... to keep the lsp from bitching at me 'incompatible overide of method closeEvent' """
        if self.close_callback:
            self.close_callback()
        a0.accept()

    def plot_tex(self, path, tex):
        self.pdf_window.plot_tex(path, tex)

    def set_error_message(self, msg: str):
        """ Creates a pop up with message = msg """
        msg_box = QMessageBox(self)
        msg_box.setText(msg)
        msg_box.setWindowTitle("Error")
        msg_box.exec()

    def setCloseCallback(self, callback):
        self.close_callback = callback

    def bind_next_flashcard_button(self, callback: Callable[[], None]):
        """ bind next flashcard button in gui with callback function """
        self.flashcard_button_bar.connect_clicked_next_button(callback)

    def bind_prev_flashcard_button(self, callback: Callable[[], None]):
        """ bind previous flashcard button in gui with callback function """
        self.flashcard_button_bar.connect_clicked_prev_button(callback)

    def bind_show_answer_button(self, callback: Callable[[], None]):
        """ bind show answer button in gui with callback function """
        self.flashcard_button_bar.connect_clicked_show_answer_button(callback)

    def bind_show_question_button(self, callback: Callable[[], None]):
        """ bind show question button in gui with callback function """
        self.flashcard_button_bar.connect_clicked_show_question_button(callback)

    def bind_create_flashcards_button(self, callback: Callable[[], None]):
        self.config_bar.create_flashcards_button.clicked.connect(callback)

    def bind_flashcard_info_button(self, callback):
        self.top_bar.connect_clicked_info_button(callback)

    def bind_show_proof_button(self, callback):
        self.show_proof_button().clicked.connect(callback)

    def bind_launch_iterm_button(self, callback):
        if CONFIG.iterm2_enabled:
            self.config_bar.launch_iterm_button.clicked.connect(callback)

    def bind_open_main_button(self, callback):
        self.config_bar.open_main.clicked.connect(callback)

    def flashcard_type_label(self):
        return self.top_bar.flashcard_type

    def list_model(self) -> QStandardItemModel:
        return self.config_bar.filter_by_week_list_model

    def course_combo(self):
        return self.config_bar.course_combo

    def flashcard_info_button(self):
        return self.top_bar.info_button

    def pdf_viewer(self):
        return self.pdf_window.pdf_viewer

    def section_list(self):
        return self.config_bar.section_list

    def filter_by_week_list(self):
        return self.config_bar.filter_by_week_list

    def random_checkbox(self):
        return self.config_bar.random_checkbox

    def show_proof_button(self):
        return self.flashcard_button_bar.show_proof_button
