import random
import logging
import threading
import time
from pathlib import Path
from collections import deque
from typing import Deque

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from mathnotelib.exceptions import FlashcardNotFoundException


from .pipeline import ProcessingPipeline
from ..models import Flashcard, FlashcardDoubleLinkedList
from ..services import FlashcardCompiler

logger = logging.getLogger("mathnote")




#class FlashcardSession:
#    def __init__(self):
#        self.compiled_flashcards = FlashcardDoubleLinkedList()
#        self.current_card: Flashcard | None = None
#        self._terminated = False
#
#    def next(self) -> Flashcard:
#        # edge case: at first flashcard
#        if self.compiled_flashcards.current and not self.compiled_flashcards.current.data.seen: # Case occurs at  begining of flashcards
#            self.compiled_flashcards.current.data.seen = True
#            self.current_card = self.compiled_flashcards.current.data
#            return self.compiled_flashcards.current.data
#
#        while self._terminated == False:
#            print("attempting to add")
#            try:
#                print("trying to get card")
#                next = self.compiled_flashcards.get_next()
#                self.current_card = next
#                self.current_card.seen = True
#                return next
#
#            except FlashcardNotFoundException as e:
#                pass
#            time.sleep(0.25)
#        raise FlashcardNotFoundException
#
#    def prev(self):
#        prev_card = self.compiled_flashcards.get_prev()
#        self.current_card = prev_card
#        self.current_card.seen = True
#        return prev_card
#
#    def add_card(self, card: Flashcard):
#        print("add")
#        self.compiled_flashcards.prepend(card)
#
#    def terminate(self):
#        self._terminated = True
#        self.compiled_flashcards.clear()
#
#    def start(self):
#        self._terminated = False
#        self.current_card = None
#
#class FlashcardWorker(QObject):
#    card_compiled = pyqtSignal(Flashcard)
#    finished = pyqtSignal()
#
#    def __init__(self, compiler: FlashcardCompiler, cancel_event: threading.Event, session: FlashcardSession):
#        super().__init__()
#        self.session = session
#        self.compiler = compiler
#        self._cancelled = cancel_event
#
#    @pyqtSlot()
#    def run(self, pipeline: ProcessingPipeline, shuffle=False):
#        for flash_cards in pipeline:
#            while self.session.compiled_flashcards.num_unseen_cards() > 3 and not self._cancelled.set():
#                print("sleep")
#                time.sleep(1)
#            if self._cancelled.is_set():
#                break
#            if shuffle:
#                random.shuffle(flash_cards)
#            for flashcard in flash_cards:
#                print("card")
#                self.compiler.compile_card(flashcard)
#                self.card_compiled.emit(flashcard)
#        self.finished.emit()



class FlashcardSession:
    def __init__(self, compiler: FlashcardCompiler) -> None:
        """
        -- Params --
        compiler: manages compilation of flash cards, type TexCompilationManager
        """
        self.cache_dir = Path(__file__).parent.resolve() / "cache_tex"
        self.compiler = compiler
        self.flashcards: Deque[Flashcard] = deque()
        self.compiled_flashcards: FlashcardDoubleLinkedList = FlashcardDoubleLinkedList()
        self.flashcard_lock = threading.RLock()
        self.thread_stop_event = threading.Event()
        self.current_card: Flashcard | None = None # threadsafe, never accessed by thread
        self._compile_thread = StoppableThread(callback=self._compile)
        self._macros = None

    def start(self):
        self._compile_thread.start()

    def _next_compiled_flashcard(self) -> Flashcard:
        """ Thread safe retreival of next card
        TODO: Clean this up... """
        with self.flashcard_lock:
            # if current card is compiled and has not been seen return it
            if self.compiled_flashcards.current and not self.compiled_flashcards.current.data.seen: # Case occurs at  begining of flashcards
                self.compiled_flashcards.current.data.seen = True
                self.current_card = self.compiled_flashcards.current.data
                return self.compiled_flashcards.current.data

            next_card = self.compiled_flashcards.get_next()
            self.current_card = next_card
            self.current_card.seen = True
            return next_card

    def _prev_compiled_flashcard(self) -> Flashcard:
        """ Thread safe retreival of previous card  """
        with self.flashcard_lock:
            prev_card = self.compiled_flashcards.get_prev()
            self.current_card = prev_card
            self.current_card.seen = True
            return prev_card

    def _prepend_compiled_flashcard(self, card: Flashcard) -> None:
        """ Thread safe prepend to FlashcardDoubleLinkedList """
        with self.flashcard_lock:
            self.compiled_flashcards.prepend(card)

    def _append_compiled_flashcard(self, card: Flashcard) -> None:
        """ Thread safe append to FlashcardDoubleLinkedList """
        with self.flashcard_lock:
            self.compiled_flashcards.append(card)

    def load_flashcards(self, pipeline: ProcessingPipeline, shuffle=True):
        r""" Load flash cards with raw tex. Threadsafe... hopefully as I run it on its own thread. Even though this
        is bound by CPU, threading allows for the compilation and generation process to alternate (not sure if this is actually true)
        -- Params --
        section_names: names of box's defined by user. i.e \defin{Integer}{Content} is a section called 'defin'
        """
        # Implement thread safe 'clearing'
        with self.flashcard_lock:
            self.compiled_flashcards.clear()
            self.current_card = None
            self.flashcards.clear()
        # Since FlashcardsPipeline is a generator we can not shuffle all card together.
        # As a work around paths in each batch are shuffled and as each batch is added we shuffle all batches together

        for flash_cards in pipeline:
            if shuffle:
                random.shuffle(flash_cards)
            with self.flashcard_lock:
                for flashcard in flash_cards:
                    self.flashcards.append(flashcard)
            logger.debug(f"Loaded flashcards: {flash_cards}")

    def next_flashcard(self) -> Flashcard:
        """ Retreive next flashcard, implements blocking behaviour when there are no compiled cards however one is currently being compiled """
        # If there is a flash card with compiled latex return that card
        while len(self.flashcards) != 0 and (not self.compiled_flashcards.current or not self.compiled_flashcards.current.next):
            logger.debug(f"{repr(self.next_flashcard)} waiting on conditions self.flashcards and (not self.compiled_flashcards or not self.compiled_flashcards.current.next)")
            time.sleep(1)
        return self._next_compiled_flashcard()

    def prev_flashcard(self) -> Flashcard:
        """ Returns previous compiled flashcard """
        return self._prev_compiled_flashcard()

    def _count_precompiled_cards(self):
        """ Returns number of compiled cards that are 'next' and have not been viewed in the FlashcardDoubleLinkedList
        TODO: Decide if 'compiled' cards with no pdf path count.. probably not however we currently count them """
        counter = 0
        card = None if self.compiled_flashcards.current is None else self.compiled_flashcards.current.next
        while card and not card.data.seen:
            card = card.next
            counter+=1

        return counter

    def stop(self):
        self._compile_thread.stop()

    # TODO
    def _compile(self, event: threading.Event, compile_num=2):
        """ Inteded to be executed by StoppableThread
        -- Params --
        compile_num: The number of flashcards that should be pre-compiled. If the user has seen 8 flashcards and compile_num=2, flashcards 1-10 will have compiled latex (assuming thread has time to pre-compile)
        event: threading.Event; when set breaks the function out of a 'waiting state'.
        """
        logger.debug(f"Calling {self._compile}(event={event}, compile_num={compile_num})")
        while self._count_precompiled_cards() > compile_num or len(self.flashcards) == 0:
            logger.debug(f"_compile waiting for len(self.compiled_flashcards)= {len(self.compiled_flashcards)} < {compile_num}=compiled_num or len(flashcards)={len(self.flashcards)} == 0")
            if event.is_set():
               break

            time.sleep(1)

        with self.flashcard_lock:
            if len(self.flashcards) == 0:
                return
            card = self.flashcards.popleft()
            try:
                self.compiler.compile_card(card)
                self._prepend_compiled_flashcard(card)

            except Exception as e:
                msg = str(e)
                if len(msg) > 1000:
                    msg = msg[:1000]
                logger.debug(f"Failed to compile: {msg}")
            return None

class StoppableThread(threading.Thread):
    """
    Accepts kwarg 'callback' of type Callable that is called by StoppableThread._run() on every loop for which the _stop_event
    is not set. The callback must accept one parameter: threading.Event(). If the callback implements its own blocking behaviour it must
    break out of that state when even it set (see FlashcardModel.compile)
    """
    def __init__(self, *args, **kwargs):
        self._stop_event = threading.Event()
        self._stopped_properly = threading.Event()
        self.inner_target = kwargs.get("callback")
        del kwargs["callback"]
        kwargs["target"] = self._run
        super().__init__(*args, **kwargs)

    def stopped(self) -> bool:
        return self._stop_event.is_set()

    def _run(self):
        logger.debug(f"Starting {self.__class__.__name__}")
        while not self.stopped():
            if self.inner_target:
                self.inner_target(self._stop_event)
        self._stopped_properly.set()

    def wait_for_stop(self):
        """ waits for stop event and resets events """
        logger.debug(f"{self.__class__.__name__} waiting for stop")
        self._stopped_properly.wait()

    def reset_events(self):
        logger.debug(f"reseting {self.__class__.__name__} events")
        self._stop_event.clear()
        self._stopped_properly.clear()

    def stop(self):
        logger.debug(f"Setting {self.__class__.__name__} stop event")
        self._stop_event.set()
