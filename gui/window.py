from PyQt6.QtWidgets import (QComboBox, QHBoxLayout, QSizePolicy, QSpacerItem, QVBoxLayout, QWidget, QPushButton,
                             QMainWindow, QSpacerItem, QSizePolicy, QScrollArea)
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QPainter, QPalette
import sys
from pathlib import Path
from typing import Optional

class CustomPdfView(QWidget):
    def __init__(self, pdf_document):
        super().__init__()
        layout = QVBoxLayout(self)
        self.pdf_view = QPdfView(self)
        self.pdf_view.setStyleSheet("background-color: white;")
        self.pdf_view.setDocument(pdf_document)
        layout.addWidget(self.pdf_view)
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUi()

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

    def _set_config_layout(self):
        config_layout = QVBoxLayout()
        self.dropdown = QComboBox()
        self.dropdown.addItems(['item1', 'item2'])
        config_layout.addWidget(self.dropdown)
        config_layout.addStretch()
        return config_layout

    def _set_flashcard_layout(self):
        main_flashcard_layout = QVBoxLayout()
        self.next_flashcard_button = QPushButton("Next", self)
        self.next_flashcard_button.setFixedSize(75, 30)
        self.prev_flashcard_button = QPushButton("Prev", self)
        self.prev_flashcard_button.setFixedSize(75, 30)
        self.show_answer_button = QPushButton("Show Answer", self)
        self.show_quesetion_button = QPushButton("Show Question", self)

        button_layout_next_prev = QHBoxLayout()
        button_layout_question_answer = QHBoxLayout()
        button_layout_question_answer.addStretch()
        button_layout_question_answer.addWidget(self.show_answer_button)
        button_layout_question_answer.addWidget(self.show_quesetion_button)
        button_layout_question_answer.addStretch()
        button_layout_next_prev.addStretch()
        button_layout_next_prev.addWidget(self.prev_flashcard_button)
        button_layout_next_prev.addWidget(self.next_flashcard_button)
        button_layout_next_prev.addStretch()

        self.scroll_area = QScrollArea(self.widget)
        # Setting pdf_viewer parent to scroll_area allows QPdfView scroll bar. Setting hidden=True hides scroll_area box used to scroll gui window
        self.scroll_area.setHidden(True)
        self.pdf_viewer = QPdfView(self.scroll_area)

        pallete = QPalette()
        pallete.setBrush(QPalette.ColorRole.Dark, QColor('white'))
        self.pdf_viewer.setPalette(pallete)

        main_flashcard_layout.addLayout(button_layout_question_answer)
        main_flashcard_layout.addWidget(self.pdf_viewer, 3)
        main_flashcard_layout.addLayout(button_layout_next_prev)
        return main_flashcard_layout

    def _load_pdf(self, pdf_path: str):
        if not Path(pdf_path).is_file():
            raise ValueError("Should be of type str not pathlib.Path")
        pdf_document = QPdfDocument(self)
        load_status = pdf_document.load(pdf_path)
        if load_status == QPdfDocument.Error.None_:
            self.pdf_viewer.setDocument(pdf_document)
            self.pdf_viewer.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        else:
            print(load_status)
            print("failed to load pdf")

    def plot_tex(self, pdf_path: str):
        self._load_pdf(pdf_path)
#        self.canvas.plot_latex(tex)

    def bind_next_flashcard_button(self, callback):
        self.next_flashcard_button.clicked.connect(callback)

    def bind_prev_flashcard_button(self, callback):
        self.prev_flashcard_button.clicked.connect(callback)

    def bind_show_answer_button(self, callback):
        self.show_answer_button.clicked.connect(callback)

    def bind_show_question_button(self, callback):
        self.show_quesetion_button.clicked.connect(callback)


#    def contextMenuEvent(self, event):
#        context = QMenu(self)
#        context.addAction(QAction("Test1", self))
#        context.addAction(QAction("Test1", self))
#        context.exec(event.globalPos())
