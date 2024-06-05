from enum import EnumMeta
from .window import MainWindow
from .flashcard_model import FlashcardModel
from pathlib import Path
from PyQt5.QtWidgets import QApplication
import sys
import time
from ..Course import parse_tex

class FlashcardController:
    def __init__(self, view, model) -> None:
        self.model = model
        self.view = view
        self.app = QApplication([])
        self.current_card = self.model.next_flashcard() # fix this
        self.model.load_flashcards(['defin'])
        self.view.bind_next_flashcard_button(self.next_flashcard)
        self.view.bind_prev_flashcard_button(self.prev_flashcard)
        self.view.bind_show_answer_button(self.show_answer)
        self.view.bind_show_question_button(self.show_question)


    def run(self):
        self.view.show()
        sys.exit(self.app.exec())

    def next_flashcard(self):
        self.current_card = self.model.next_flashcard()
        self.show_question()

    def prev_flashcard(self):
        self.current_card = self.model.prev_flashcard()
        self.show_answer()

    def show_question(self):
        print(self.current_card.question)
        self.view.plot_tex(self.current_card.question)

    def show_answer(self):
        self.view.plot_tex(self.current_card.answer.replace("\n", ''))






if __name__ == '__main__':
    path = Path("/Users/joshuataylor/documents/notes/uofc/math-445/lectures/lec_03.tex")
    flashcard_model = FlashcardModel([path])
    window = MainWindow()

    controller = FlashcardController(window, flashcard_model)
    controller.run()

