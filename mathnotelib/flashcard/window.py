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


TAB_BTN_EMPTY_CSS = """
QPushButton {
    border: none;
    background: transparent;
    border-radius: 4px;
}
QPushButton:hover {
    background: transparent;
    border-radius: 4px;
}

QPushButton:pressed {
    background: transparent;
    border-radius: 4px;
}
"""




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
        self.btn.setFixedWidth(80)
        self.btn.setFlat(True)
        self.btn.setFixedHeight(29)
        self.btn.setStyleSheet(TAB_BTN_EMPTY_CSS)
        main_layout.addWidget(self.btn)
        self.setLayout(main_layout)



class FlashcardConfigWidget(QWidget):

    def __init__(self) -> None:
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)
        self.initUi()

    def initUi(self):


        self.setContentsMargins(0, 0, 0, 0)
        self.setFixedWidth(160)
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.button_layout = QHBoxLayout()
        self.button_layout.setContentsMargins(0, 0, 0, 0)

        self.course_btn = TabButton("Courses")
        self.deck_btn = TabButton("Deck")


        self.command_bar = CommandBar()

        self.course_btn.btn.clicked.connect(lambda: self.toggle(self.course_btn.label))
        self.deck_btn.btn.clicked.connect(lambda: self.toggle(self.deck_btn.label))

        self.button_layout.addWidget(self.course_btn)
        self.button_layout.addWidget(self.deck_btn)

        self.course_config = CourseFlashcardConfigWidget()
        self.deck_config = DeckFlashcardConfigWidget()
        self.main_layout.addLayout(self.button_layout)
        self.main_layout.addWidget(self.course_config)
        self.main_layout.addWidget(self.deck_config)
        self.main_layout.addWidget(self.command_bar)

        self.deck_config.hide()
        self.course_btn.setStyleSheet("background-color: #555;")

        self.setLayout(self.main_layout)


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

class SectionListWidget(QWidget):
    def __init__(self, section_names: list[str]):
        super().__init__()
        self.section_names = section_names

        self.initUi()


    def initUi(self):
        self.setContentsMargins(0, 0, 0, 0)
        self.setFixedWidth(150)

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

        self.section_list.setMaximumWidth(125)
        self.section_list.setMaximumHeight(150)
        self.section_list.setContentsMargins(0, 8, 0, 12)
        self.section_list.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.section_list_label.setContentsMargins(0, 12, 0, 8)
        self.section_list_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        main_layout.addWidget(self.section_list_label)
        main_layout.addWidget(self.section_list)

class DeckFlashcardConfigWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.initUi()

    def initUi(self):
        self.setContentsMargins(0, 0, 0, 0)
        self.setFixedWidth(150)

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





BUTTON_CSS = """
QPushButton {
    background: #555;
    color: #ddd;
    border: none;
    border-radius: 4px;
    font-size: 13px;
    padding: 4px 10px;
}
QPushButton:hover {
    background: #666;
    border-radius: 4px;
}
QPushButton:pressed {
    background: #777;
    border-radius: 4px;
}
"""


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

    def connect_clicked_show_question_button(self, func):
        self.show_question_button.clicked.connect(func)

    def connect_clicked_show_answer_button(self, func):
        self.show_answer_button.clicked.connect(func)

    def connect_clicked_next_button(self, func):
        self.next_flashcard_button.clicked.connect(func)

    def connect_clicked_prev_button(self, func):
        self.prev_flashcard_button.clicked.connect(func)

class InfoBar(QWidget):
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
        self.bar_layout.addStretch()
        self.bar_layout.addWidget(self.flashcard_type)
        self.bar_layout.addStretch()
        self.bar_layout.addStretch()
        self.bar_layout.addWidget(self.info_button)

    def connect_clicked_info_button(self, callback):
        self.info_button.connect(callback)


class PdfWindow(QWidget):
    def __init__(self, widget):
        super().__init__()
        self.parent_widget = widget
        self.initUi()

    def initUi(self):
        self.setContentsMargins(0, 0, 0, 0)
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

    def _load_pdf(self, pdf_path: Path, markdown: TrackedText) -> QPdfDocument.Error:
        """ Loads pdf into pdf_viewer and set viewer settings
        -- Params --
        pdf_path: (str) absolute path to pdf
        returns: QPdfDocument.Error
        """
        pdf_document = QPdfDocument(self)
        load_status = pdf_document.load(str(pdf_path))

        if load_status == QPdfDocument.Error.None_:
            self.document = pdf_path
            self.pdf_viewer.setDocument(pdf_document)
            # TODO: Latex does can not generate files with fixed width and auto height so we use this hack
            if len(markdown) < 100 and markdown.filetype() == FileType.LaTeX:
                self.pdf_viewer.setZoomMode(QPdfView.ZoomMode.Custom)
                self.pdf_viewer.setZoomFactor(ZOOM_FACTOR)
            else:
                self.pdf_viewer.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        return load_status

    def display_pdf(self, pdf_path: Path, markdown: TrackedText):
        """
        -- Params --
        pdf_path: absolute path to pdf
        return: load status
        """
#        target = card.pdf_question_path if question else card.pdf_answer_path # I dont like this. Plot tex should only take in filepath?
        load_status = self._load_pdf(pdf_path, markdown)
        if load_status != QPdfDocument.Error.None_:
            self.document = None
            raise LaTeXCompilationError(f"Failed to compile card: {pdf_path}. Load status: {load_status}")


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


MAIN_WINDOW_CSS = """
QMainWindow {
        background-color: #2E2E2E;
        }
"""


# Yeah... idk about all these one line methods
class FlashcardMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.close_callback = None
        self.initUi()

    def initUi(self):
        self.setStyleSheet(MAIN_WINDOW_CSS)
        self.widget = QWidget()
        self.main_layout = QHBoxLayout(self.widget)
        self.main_flashcard_layout = QVBoxLayout()
        self.resize(1000, 600)
        self.setMinimumSize(1000, 600)
        self.setContentsMargins(8, 8, 8, 8)
        self.setCentralWidget(self.widget)

        # Create widgets
        self.flashcard_button_bar = HButtonBar()
        self.top_bar = InfoBar()
        self.pdf_window = PdfWindow(self.widget)
        self.config_bar = FlashcardConfigWidget()
        self.course_config = self.config_bar.course_config

        # Add widgets
        self.main_flashcard_layout.addWidget(self.top_bar)
        self.main_flashcard_layout.addWidget(self.pdf_window, 3)
        self.main_flashcard_layout.addWidget(self.flashcard_button_bar)
        self.main_layout.addWidget(self.config_bar)

        self.main_layout.addLayout(self.main_flashcard_layout)


    @property
    def document(self):
        return self.pdf_window.document

    def closeEvent(self, a0):
        """a0 is an event. Why the name... to keep the lsp from bitching at me 'incompatible overide of method closeEvent' """
        if self.close_callback:
            self.close_callback()
        a0.accept()

    def display_pdf(self, path: Path, markdown: TrackedText):
        self.pdf_window.display_pdf(path, markdown)

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
        self.config_bar.command_bar.create_flashcards_button.clicked.connect(callback)

    def bind_flashcard_info_button(self, callback):
        self.top_bar.connect_clicked_info_button(callback)

    def bind_show_proof_button(self, callback):
        self.show_proof_button().clicked.connect(callback)

    def bind_launch_iterm_button(self, callback):
        if CONFIG.iterm2_enabled:
            self.course_config.launch_iterm_button.clicked.connect(callback)

    def flashcard_type_label(self):
        return self.top_bar.flashcard_type

    def list_model(self) -> QStandardItemModel:
        return self.course_config.filter_by_week_list_model

    def course_combo(self):
        return self.course_config.course_combo

    def flashcard_info_button(self):
        return self.top_bar.info_button

    def pdf_viewer(self):
        return self.pdf_window.pdf_viewer

    def section_list(self):
        return self.course_config.section_list

    def filter_by_week_list(self):
        return self.course_config.filter_by_week_list

    def random_checkbox(self):
        return self.course_config.random_checkbox

    def show_proof_button(self):
        return self.flashcard_button_bar.show_proof_button
