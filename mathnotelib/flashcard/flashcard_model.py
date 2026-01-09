import hashlib
import os
import random
import threading
import time
import logging
from pathlib import Path
from typing import Optional, Deque, OrderedDict
from collections import deque

from mathnotelib._enums import FileType

from ..models import Flashcard, FlashcardDoubleLinkedList
from ..config import CONFIG
from ..services import FlashcardCompiler
from ..utils import StoppableThread
from ..pipeline import FlashcardBuilderStage, CleanStage, DataGenerator, ProcessingPipeline, MainSectionFinder, get_hack_macros, FlashcardFormatStage

logger = logging.getLogger("mathnote")




# build into stage

# Global state?
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
        self.current_card: Optional[Flashcard] = None # threadsafe, never accessed by thread
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

    def load_flashcards(self, section_names: list[str], paths: list[Path], shuffle=True) -> None:
        r""" Load flash cards with raw tex. Threadsafe... hopefully as I run it on its own thread. Even though this
        is bound by CPU, threading allows for the compilation and generation process to alternate (not sure if this is actually true)
        -- Params --
        section_names: names of box's defined by user. i.e \defin{Integer}{Content} is a section called 'defin'
        """
        logger.debug(f"Calling load_flashcards(section_names={section_names}, paths={paths})")
        # Implement thread safe 'clearing'
        with self.flashcard_lock:
            self.compiled_flashcards.clear()
            self.current_card = None
            self.flashcards.clear()
        # Since FlashcardsPipeline is a generator we can not shuffle all card together.
        # As a work around paths in each batch are shuffled and as each batch is added we shuffle all batches together
        if shuffle:
            random.shuffle(paths)

        data_iterable = DataGenerator(paths)
        # TODO fix get_hack_macros
#        clean_data_stage = CleanStage(self.macros | get_hack_macros())
        build_stage = FlashcardBuilderStage(section_names)
        format_stage = FlashcardFormatStage()

        # TODO why?
        build_stage.add_subsection_finder("PROOF", ["THEOREM", "PROPOSITION", "LEMMA", "COROLLARY"])
        pipeline = ProcessingPipeline(data_iterable)
#        pipeline.add_stage(clean_data_stage)
        pipeline.add_stage(build_stage)
        pipeline.add_stage(format_stage)
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


    def _get_all_flashcard_paths(self):
        paths = []
        for node in self.compiled_flashcards:
            card = node.data
            if card.pdf_answer_path:
                paths.append(card.pdf_answer_path)
            if card.pdf_question_path:
                paths.append(card.pdf_question_path)
        return paths

    def stop(self):
        self._compile_thread.stop()

    # TODO: prevent other methods from calling?
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
            logger.debug(repr(card))
            try:
                self.compiler.compile_card(card)
                logger.debug(f"Compiled card: {repr(card)}")
                self._prepend_compiled_flashcard(card)

            except Exception as e:
                msg = str(e)
                if len(msg) > 1000:
                    msg = msg[:1000]
                logger.error(f"Failed to compile: {msg}")
#            flashcard_hash = (set(self.compiler.get_hash(str(flashcard.question)) for flashcard in self.flashcards)
#                              | set(self.compiler.get_hash(str(value)) for _card in self.flashcards for value in _card.additional_info.values()))

            return None
