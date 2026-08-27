import random
import logging
import threading
import time
from pathlib import Path
from collections import deque
from typing import Deque

from PyQt6.QtCore import QObject, pyqtSignal

from .pipeline import ProcessingPipeline
from ..models import Flashcard, FlashcardDoubleLinkedList
from ..services import FlashcardCompiler
from ..config import Config
from .._enums import FileType

logger = logging.getLogger("mathnote")


"""
This code is absolutely fucked. e.g., if next_flashcard is called to soon after the load_flashcards thread we fail to wait for the first flashcard to be compiledb loop and an error is raised,
informing the user all flashcards have already been viewed. To "solve" this we utilize time.sleep... (see controllers.py).
The methods _compile, load_flashcards, next_flashcard are all fragile.
"""
class FlashcardSession(QObject):
    pos = pyqtSignal(int, int)

    def __init__(self, compiler: FlashcardCompiler) -> None:
        """
        -- Params --
        compiler: manages compilation of flash cards, type TexCompilationManager
        """
        super().__init__()
        self.cache_dir = Path(__file__).parent.resolve() / "cache_tex"
        self.compiler = compiler
        self.flashcards: Deque[Flashcard] = deque()
        self.compiled_flashcards: FlashcardDoubleLinkedList = FlashcardDoubleLinkedList()
        self.flashcard_lock = threading.RLock()
        self.current_card: Flashcard | None = None # threadsafe, never accessed by thread
        self._compile_thread: StoppableThread | None = None
        self._macros = None
        self._total = 0
        self._pos = 0
        self._pipe_finished = True

    def load_flashcards(self, pipeline: ProcessingPipeline, shuffle=True):
        r""" Load flash cards with raw tex. Threadsafe... hopefully as I run it on its own thread. Even though this
        is bound by CPU, threading allows for the compilation and generation process to alternate (not sure if this is actually true)
        -- Params --
        section_names: names of box's defined by user. i.e \defin{Integer}{Content} is a section called 'defin'
        """
        # Reset
        if self._compile_thread is not None and not self._compile_thread.is_stopped():
            self._compile_thread.stop()
            self._compile_thread.wait_for_stop()

        with self.flashcard_lock:
            self.compiled_flashcards.clear()
            self.current_card = None
            self.flashcards.clear()
            self._pos = 0
            self._pipe_finished = False
            self._total = 0

        # Set new thread
        self._compile_thread = StoppableThread(callback=self._compile)
        self._compile_thread.start()

        # Since FlashcardsPipeline is a generator we can not shuffle all card together.
        # As a work around paths in each batch are shuffled and as each batch is added we shuffle all batches together
        for flash_cards in pipeline:
            if shuffle:
                random.shuffle(flash_cards)
            with self.flashcard_lock:
                for flashcard in flash_cards:
                    self.flashcards.append(flashcard)
            self._total += len(flash_cards)

        self._pipe_finished = True

    def next_flashcard(self, first=False) -> Flashcard:
        if first:
            while self.compiled_flashcards.current is None and self._compile_thread is not None:
                time.sleep(0.25)
        else:
            while (self.compiled_flashcards.current is None or self.compiled_flashcards.current.next is None) and self._compile_thread is not None:
                time.sleep(0.25)

        with self.flashcard_lock:
            # if current card is compiled and has not been seen return it
            if self.compiled_flashcards.current and not self.compiled_flashcards.current.data.seen: # Case occurs at  begining of flashcards
                self.compiled_flashcards.current.data.seen = True
                self.current_card = self.compiled_flashcards.current.data
                next_card = self.compiled_flashcards.current.data
                self._pos += 1

            else:
                next_card = self.compiled_flashcards.get_next()
                self._pos += 1

        self.current_card = next_card
        self.current_card.seen = True
        self.pos.emit(self._pos, self._total)
        return next_card

    def prev_flashcard(self) -> Flashcard:
        """ Returns previous compiled flashcard """
        with self.flashcard_lock:
            prev_card = self.compiled_flashcards.get_prev()
            self.current_card = prev_card
            self.current_card.seen = True
        self._pos -= 1
        self.pos.emit(self._pos, self._total)
        return prev_card

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
        if self._compile_thread is not None:
            self._compile_thread.stop()

    # TODO
    def _compile(self, event: threading.Event, compile_num=2):
        """ Inteded to be executed by StoppableThread
        -- Params --
        compile_num: The number of flashcards that should be pre-compiled. If the user has seen 8 flashcards and compile_num=2, flashcards 1-10 will have compiled latex (assuming thread has time to pre-compile)
        event: threading.Event; when set breaks the function out of a 'waiting state'.
        """
        logger.debug(f"Calling {self._compile}(event={event}, compile_num={compile_num})")
        while self._count_precompiled_cards() > compile_num or (len(self.flashcards) == 0 and not self._pipe_finished):
            logger.debug(f"_compile waiting for len(self.compiled_flashcards)= {len(self.compiled_flashcards)} < {compile_num}=compiled_num or len(flashcards)={len(self.flashcards)} == 0")
            if event.is_set():
               break
            time.sleep(0.25)

        with self.flashcard_lock:

            if self._pipe_finished and self._pos == self._total:
                event.set()
                self._compile_thread = None
                return

            if len(self.flashcards) == 0:
                return

            card = self.flashcards.popleft()
            try:
                self.compiler.compile_card(card)
                with self.flashcard_lock:
                    self.compiled_flashcards.prepend(card)

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
    break out of that state when event it set (see FlashcardSession._compile)
    """
    def __init__(self, *args, **kwargs):
        self._stop_event = threading.Event()
        self._stopped_properly = threading.Event()
        self.inner_target = kwargs.get("callback")
        if "callback" in kwargs:
            del kwargs["callback"]
        kwargs["target"] = self._run
        super().__init__(*args, **kwargs)

    def is_stopped(self) -> bool:
        return self._stop_event.is_set()

    def _run(self):
        logger.debug(f"Starting {self.__class__.__name__}")
        while not self.is_stopped():
            if self.inner_target:
                self.inner_target(self._stop_event)
        self._stopped_properly.set()

    def wait_for_stop(self):
        """ waits for stop event and resets events """
        logger.debug(f"{self.__class__.__name__} waiting for stop")
        self._stopped_properly.wait()

    def stop(self):
        logger.debug(f"Setting {self.__class__.__name__} stop event")
        self._stop_event.set()



class DeckRepository:
    def __init__(self, config: Config):
        self.config = config
        self.root_deck_path = config.root_path / "Decks" #TODO: move this to config section
        self._decks: dict[str, Path] = {}

    @property
    def decks(self) -> dict[str, Path]:
        if len(self._decks) == 0:
            decks = self._load_decks()
            self._decks = decks
            return self._decks
        else:
            return self._decks

    def _load_decks(self) -> dict[str, Path]:
        decks = {}
        for file in self.root_deck_path.iterdir():
            if file.suffix in [".typ", ".tex"]:
                decks[file.stem] = file
        return decks

    def new_deck(self, name: str, ftype: FileType):
        names = self.decks.keys()
        if name in names:
            raise ValueError(f"Deck '{name}' already exists")
        new_file = self.root_deck_path / f"{name}{ftype.extension}"
        new_file.touch()
        self._decks = self._load_decks()

    def rename_deck(self, old_name: str, new_name: str):
        old_file = self.decks.get(old_name)
        if old_file is None:
            raise ValueError(f"Deck '{old_name}' does not exist")

        if new_name in self.decks.keys():
            raise ValueError(f"Deck '{new_name}' already exists")
        new_path = self.root_deck_path / f"{new_name}{old_file.suffix}"
        old_file.rename(new_path)


    def delete_deck(self, name: str):
        file = self.decks.get(name)
        # Should I even catch the error, or just let it get raised in unlink()?
        if file is None:
            raise ValueError(f"Deck '{name}' does not exist")
        else:
            file.unlink()


