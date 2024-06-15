from logging import log
from pathlib import Path
from types import FunctionType
from PyQt6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit, QListView, QListWidget, QListWidgetItem, QMessageBox, QSizePolicy, QSpacerItem, QVBoxLayout, QWidget, QPushButton,
                             QMainWindow, QSpacerItem, QSizePolicy, QScrollArea)
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtGui import QColor, QPainter, QPalette, QStandardItem, QStandardItemModel
from ..course.parse_tex import Flashcard
import logging

logger = logging.getLogger(__name__)

class LatexCompilationError(Exception):
    pass

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUi()
        self.close_callback = None

    def initUi(self):
        self.resize(1000, 600)
        self.setMinimumSize(400, 300)
        # create central widget and set a layout
        self.widget = QWidget()
        self.setCentralWidget(self.widget)

        main_layout = QHBoxLayout(self.widget)
        flashcard_layout = self._set_flashcard_layout()
        config_layout = self._set_config_layout()

        spacer = QSpacerItem(40, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        main_layout.addItem(spacer)
        main_layout.addLayout(flashcard_layout)
        main_layout.addLayout(config_layout)

    def setCloseCallback(self, callback):
        self.close_callback = callback

    def closeEvent(self, a0):
        """a0 is an event. Why the name... to keep the lsp from bitching at me 'incompatible overide of method closeEvent' """
        if self.close_callback:
            self.close_callback()
        a0.accept()

    def _set_config_layout(self):
        # Creating Layout
        config_layout = QVBoxLayout()
        # Creating Widgets
        self.search_bar = QLineEdit()
        course_combo_label = QLabel()
        self.course_combo= QComboBox()
        self.section_list = QListView()
        section_list_label = QLabel()
        self.create_flashcards_button = QPushButton("Create Flashcards")

#        self.dropdown.setMaximumWidth(100)
        self.search_bar.setMaximumWidth(100)
        course_combo_label.setText("Select Course")
        section_list_label.setText("Select Section")
        self.search_bar.setPlaceholderText("Search...")

        section_list_model = QStandardItemModel()
        self.section_list_items = ["definition", "theorem", "derivation", "all"] # Make sure to map this
        for item in self.section_list_items:
            list_item = QStandardItem(item)
            list_item.setCheckable(True)
            section_list_model.appendRow(list_item)
        self.section_list.setModel(section_list_model)

        self.section_list.setMaximumWidth(100)
        self.section_list.setMaximumHeight(100)
        #Add Widgets to layout
        config_layout.addWidget(self.search_bar)
        config_layout.addWidget(course_combo_label)
        config_layout.addWidget(self.course_combo)
        config_layout.addWidget(section_list_label)
        config_layout.addWidget(self.section_list)
        config_layout.addWidget(self.create_flashcards_button)
        config_layout.addStretch()
        return config_layout


    def _set_flashcard_layout(self):
        # Creating layouts
        main_flashcard_layout = QVBoxLayout()
        button_layout_next_prev = QHBoxLayout()
        button_layout_question_answer = QHBoxLayout()
        # Creating Widgets
        self.next_flashcard_button = QPushButton("Next", self)
        self.prev_flashcard_button = QPushButton("Prev", self)
        self.show_answer_button = QPushButton("Show Answer", self)
        self.show_quesetion_button = QPushButton("Show Question", self)
        self.scroll_area = QScrollArea(self.widget)
        self.pdf_viewer = QPdfView(self.scroll_area)
        # Setting Widget Style
        pallete = QPalette()
        pallete.setBrush(QPalette.ColorRole.Dark, QColor('white'))
        self.pdf_viewer.setPalette(pallete)
        # Setting other widget styles
        self.prev_flashcard_button.setFixedSize(75, 30)
        self.next_flashcard_button.setFixedSize(75, 30)
        # Setting pdf_viewer parent to scroll_area allows QPdfView scroll bar. Setting hidden=True hides scroll_area box used to scroll gui window
        self.scroll_area.setHidden(True)

        # Adding widgets and stretch
        button_layout_question_answer.addStretch()
        button_layout_question_answer.addWidget(self.show_answer_button)
        button_layout_question_answer.addWidget(self.show_quesetion_button)
        button_layout_question_answer.addStretch()
        button_layout_next_prev.addStretch()
        button_layout_next_prev.addWidget(self.prev_flashcard_button)
        button_layout_next_prev.addWidget(self.next_flashcard_button)
        button_layout_next_prev.addStretch()
        # Adding Layouts
        main_flashcard_layout.addLayout(button_layout_question_answer)
        main_flashcard_layout.addWidget(self.pdf_viewer, 3)
        main_flashcard_layout.addLayout(button_layout_next_prev)
        return main_flashcard_layout

    def _load_pdf(self, pdf_path: str) -> QPdfDocument.Error:
        """ Loads pdf into pdf_viewer and sets some viewer settings
        -- Params --
        :pdf_path (str): absolute path to pdf
        :returns: QPdfDocument.Error
        """
        if pdf_path is None:
            return QPdfDocument.Error.FileNotFound

        pdf_document = QPdfDocument(self)
        load_status = pdf_document.load(pdf_path)

        if load_status == QPdfDocument.Error.None_:
            self.pdf_viewer.setDocument(pdf_document)
#            self.pdf_viewer.setZoomMode(QPdfView.ZoomMode.FitToWidth)
            self.pdf_viewer.setZoomMode(QPdfView.ZoomMode.FitInView)
            self.pdf_viewer.setZoomFactor(1.0)
        return load_status

    def plot_tex(self, pdf_path):
        """
        -- Params --
        :pdf_path (str): absolute path to pdf
        :question (bool): True to display question, else display answer
        :return load status
        """
#        target = card.pdf_question_path if question else card.pdf_answer_path # I dont like this. Plot tex should only take in filepath?

        load_status = self._load_pdf(pdf_path)
        if load_status != QPdfDocument.Error.None_:
            raise LatexCompilationError(f"Failed to compile card: {pdf_path}. Load status: {load_status}")

    def set_error_message(self, msg: str):
        """ Creates a pop up with message = msg """
        msg_box = QMessageBox(self)
        msg_box.setText(msg)
        msg_box.exec()

    def bind_next_flashcard_button(self, callback: FunctionType): # FunctionType or Callable? Should google this at some point...
        """ bind next flashcard button in gui with callback function """
        self.next_flashcard_button.clicked.connect(callback)

    def bind_prev_flashcard_button(self, callback: FunctionType):
        """ bind previous flashcard button in gui with callback function """
        self.prev_flashcard_button.clicked.connect(callback)

    def bind_show_answer_button(self, callback: FunctionType):
        """ bind show answer button in gui with callback function """
        self.show_answer_button.clicked.connect(callback)

    def bind_show_question_button(self, callback: FunctionType):
        """ bind show question button in gui with callback function """
        self.show_quesetion_button.clicked.connect(callback)

    def bind_create_flashcards_button(self, callback: FunctionType):
        self.create_flashcards_button.clicked.connect(callback)


#    def contextMenuEvent(self, event):
#        context = QMenu(self)
#        context.addAction(QAction("Test1", self))
#        context.addAction(QAction("Test1", self))
#        context.exec(event.globalPos())
