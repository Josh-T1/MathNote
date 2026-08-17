import random
import logging
import threading
import time

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from mathnotelib.exceptions import FlashcardNotFoundException


from .pipeline import ProcessingPipeline
from ..models import Flashcard, FlashcardDoubleLinkedList
from ..services import FlashcardCompiler

logger = logging.getLogger("mathnote")


class FlashcardWorker(QObject):
    card_compiled = pyqtSignal(Flashcard)
    finished = pyqtSignal()

    def __init__(self, compiler: FlashcardCompiler, cancel_event: threading.Event):
        super().__init__()
        self.compiler = compiler
        self._cancelled = cancel_event

    @pyqtSlot()
    def run(self, pipeline: ProcessingPipeline, shuffle=False):
        for flash_cards in pipeline:
            if self._cancelled.is_set():
                break
            if shuffle:
                random.shuffle(flash_cards)
            for flashcard in flash_cards:
                self.compiler.compile_card(flashcard)
                self.card_compiled.emit(flashcard)
        self.finished.emit()


class FlashcardSession:
    def __init__(self):
        self.compiled_flashcards = FlashcardDoubleLinkedList()
        self.current_card: Flashcard | None = None
        self._terminated = False

    def next(self) -> Flashcard:
        # edge case: at first flashcard
        if self.compiled_flashcards.current and not self.compiled_flashcards.current.data.seen: # Case occurs at  begining of flashcards
            self.compiled_flashcards.current.data.seen = True
            self.current_card = self.compiled_flashcards.current.data
            return self.compiled_flashcards.current.data

        while self._terminated == False:
            try:
                next = self.compiled_flashcards.get_next()
                self.current_card = next
                self.current_card.seen = True
                return next

            except FlashcardNotFoundException as e:
                pass
            time.sleep(0.25)
        raise FlashcardNotFoundException

    def prev(self):
        prev_card = self.compiled_flashcards.get_prev()
        self.current_card = prev_card
        self.current_card.seen = True
        return prev_card

    def add_card(self, card: Flashcard):
        self.compiled_flashcards.prepend(card)

    def terminate(self):
        self._terminated = True
        self.compiled_flashcards.clear()

    def start(self):
        self._terminated = False
        self.current_card = None
