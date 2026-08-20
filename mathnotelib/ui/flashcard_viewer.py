import logging
from pathlib import Path

from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QMessageBox, QStackedWidget, QVBoxLayout,
                             QWidget, QPushButton, QScrollArea)
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor, QPalette

from .style import BUTTON_CSS
from ..models import Flashcard, FlashcardSideName
from ..ui import constants




logger = logging.getLogger("mathnote")


ZOOM_FACTOR = 3

class PdfWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.document: QPdfDocument | None = None
        self.initui()

    def initui(self):
        self.pdf_layout = QHBoxLayout()
        self.pdf_layout.setContentsMargins(0, 0, 0, 0)
        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.pdf_layout)

        # create widgets
        self.scroll_area = QScrollArea()
        self.pdf_viewer = QPdfView(self.scroll_area)
        self._palette = QPalette()

        # configure widgets
        self._palette.setBrush(QPalette.ColorRole.Dark, QColor('white'))
        self.pdf_viewer.setPalette(self._palette)
        # setting pdf_viewer parent to scroll_area allows qpdfview scroll bar. setting hidden=true hides scroll_area box used to scroll gui window
        self.scroll_area.setHidden(True)

        # add widgets
        self.pdf_layout.addWidget(self.pdf_viewer)

    def _load_pdf(self, pdf_path: Path, force_zoom=False) -> QPdfDocument.Error:
        """ loads pdf into pdf_viewer and set viewer settings
        -- params --
        pdf_path: (str) absolute path to pdf
        returns: qpdfdocument.error
        """
        pdf_document = QPdfDocument(self)
        load_status = pdf_document.load(str(pdf_path))

        if load_status == QPdfDocument.Error.None_:
            self.document = pdf_document
            self.pdf_viewer.setDocument(pdf_document)
            # todo: latex does can not generate files with fixed width and auto height so we use this hack
            if force_zoom:
                self.pdf_viewer.setZoomMode(QPdfView.ZoomMode.Custom)
                self.pdf_viewer.setZoomFactor(ZOOM_FACTOR)
            else:
                self.pdf_viewer.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        return load_status

    def display_pdf(self, pdf_path: Path, force_zoom=False):
        """
        -- params --
        pdf_path: absolute path to pdf
        return: load status
        """
        load_status = self._load_pdf(pdf_path, force_zoom=force_zoom)
        if load_status != QPdfDocument.Error.None_:
            self.document = None
            raise ValueError(f"failed to display card with path: {pdf_path}\nload status: {load_status}")

#
#
# TODO: delete
# Yeah... idk about all these one line methods
class FlashcardView(QWidget):
    def __init__(self):
        super().__init__()
        self.initUi()

    def initUi(self):
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.setLayout(self.main_layout)
        self.setContentsMargins(0, 0, 0, 0)

        self.setMinimumSize(constants.VIEWER_WIDTH, 300)
        self.resize(constants.VIEWER_WIDTH, 300)

        # Create widgets
        self.btn_bar = HButtonBar()
        self.info_bar = InfoBar()
        self.pdf_stack = QStackedWidget()
        self.pdf_window_1 = PdfWindow()
        self.pdf_window_2 = PdfWindow()
        self.pdf_window_3 = PdfWindow()


        self.pdf_stack.setContentsMargins(0, 0, 0, 0)
        self.pdf_stack.setStyleSheet("background-color: white; border: none;")
        # Add widgets
        self.pdf_stack.addWidget(self.pdf_window_1)
        self.pdf_stack.addWidget(self.pdf_window_2)
        self.pdf_stack.addWidget(self.pdf_window_3)

        self.main_layout.addWidget(self.info_bar)
        self.main_layout.addWidget(self.pdf_stack)
        self.main_layout.addWidget(self.btn_bar)

        self.btn_bar.show_question_button.clicked.connect(lambda: self.pdf_stack.setCurrentWidget(self.pdf_window_1))
        self.btn_bar.show_answer_button.clicked.connect(lambda: self.pdf_stack.setCurrentWidget(self.pdf_window_2))
        self.btn_bar.show_proof_button.clicked.connect(lambda: self.pdf_stack.setCurrentWidget(self.pdf_window_3))


    def display_compiled_card(self, card: Flashcard):
        self.pdf_stack.setCurrentWidget(self.pdf_window_1)
        question = card.sides[FlashcardSideName.QUESTION]
        answer = card.sides.get(FlashcardSideName.ANSWER)
        proof = card.sides.get(FlashcardSideName.PROOF)

        success = (answer and answer.pdf_path) or (proof and proof.pdf_path)
        if question.pdf_path is None:
            raise ValueError(f"Flashcard missing pdf_file for {question.content}")
        # TODO should it be answer
        if not success:
            raise ValueError(f"Flashcard missing answer section")

        self.pdf_window_1.display_pdf(question.pdf_path)

        if answer is not None and answer.pdf_path is not None:
            self.pdf_window_2.display_pdf(answer.pdf_path)
            self.btn_bar.show_answer_button.show()
        else:
            self.btn_bar.show_answer_button.hide()

        if proof is not None and proof.pdf_path is not None:
            self.pdf_window_3.display_pdf(proof.pdf_path)
            self.btn_bar.show_proof_button.show()
        else:
            self.btn_bar.show_proof_button.hide()
        self.info_bar.flashcard_type.setText(f"Section: {card.section_name.lower().capitalize()}")


class HButtonBar(QWidget):
    def __init__(self):
        super().__init__()
        self.initUi()


    def initUi(self):
        self.bar_layout = QHBoxLayout()
        self.bar_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.bar_layout)
        self.setFixedHeight(50)

        # Create widgets
        self.next_flashcard_button = QPushButton("Next", self)
        self.prev_flashcard_button = QPushButton("Prev", self)
        self.show_answer_button = QPushButton("Answer", self)
        self.show_question_button = QPushButton("Question", self)
        self.show_proof_button = QPushButton("Proof", self)
        buttons = [
                self.next_flashcard_button,
                self.prev_flashcard_button,
                self.show_question_button,
                self.show_answer_button,
                self.show_proof_button
                ]
        for btn in buttons:
            btn.setStyleSheet(BUTTON_CSS)
        # Configure widgets
        self.show_proof_button.setHidden(True)
        self.prev_flashcard_button.setFixedSize(75, 35)
        self.next_flashcard_button.setFixedSize(75, 35)
        self.show_proof_button.setFixedSize(85, 35)
        self.show_question_button.setFixedSize(85, 35)
        self.show_answer_button.setFixedSize(85, 35)
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


class InfoButton(QWidget):
    clicked = pyqtSignal()

    def __init__(self, diameter=16):
        super().__init__()
        self.info_button_layout = QVBoxLayout()
        self.info_button_layout.setContentsMargins(4, 4, 4, 4)
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


class InfoBar(QWidget):
    def __init__(self):
        super().__init__()
        self.initUi()


    def initUi(self):
        self.bar_layout = QHBoxLayout()
        self.bar_layout.setContentsMargins(0, 0, 0, 0)
        self.bar_layout.setSpacing(2)
        self.setFixedHeight(30)
        self.setLayout(self.bar_layout)

        # Create widgets
        self.info_button = InfoButton(diameter=16)
        self.flashcard_type = QLabel()

        # Configure widgets
        self.flashcard_type.setStyleSheet("font-size: 18px; color: white; font-family: Arial")

        # Add widgets
        self.bar_layout.addStretch()
        self.bar_layout.addWidget(self.flashcard_type)
        self.bar_layout.addStretch()
        self.bar_layout.addStretch()
        self.bar_layout.addWidget(self.info_button)
