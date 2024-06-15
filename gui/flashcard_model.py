import random
import threading
import tempfile
from pathlib import Path
import time
import subprocess
import hashlib
from ..course import parse_tex
import logging
from ..global_utils import get_config

config = get_config()

logger = logging.getLogger(__name__)


class FlashcardNotFoundException(Exception):
    pass

class StoppableThread(threading.Thread):
    """ This is some proper fuckery and poor class naming. The target function for the thread needs access to FlashcardModel properties. In order to
    de couple StoppableThread and FlashcardModel we accept a callback that is called by StoppableThread._run() on every loop for which the _stop_event
    is not set. The issue is that this specific callback requires access to StoppableThread._stop_event. Therefore we pass self._stop_event
    to callback. This works however it hardly makes sense to only accept callbacks that accept ._stop_event in the general 'StoppableThread'
    class... What about a CompileTexThread that implements FlashcardModel specific logic?...that solution also sucks
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
        logger.info(f"Starting {self.__class__.__name__}")
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

class Node:
    def __init__(self, data) -> None:
        self.data = data
        self.next: Node | None = None
        self.prev: Node | None = None

class FlashcardDoubleLinkedList:
    """ It may make more sense to use a different datastructure if we want to support slicing """
    def __init__(self, *args) -> None:
        self.head = None
        self.current = None
        for arg in args:
            self.append(arg)

    def remove(self, index: int):
        """ Remove node at index
        TODO: Should I be explicitly deleting the node? (obviously not a concern in this 'toy' project). Seems like 'del' only
        deleates reference not object..."""
        if index > len(self) or index < 0:
            raise IndexError(f"Index {index} is out of range for remove operation")

        for _index, node in enumerate(self):
            if _index != index:
                continue
            # adjust next, prev referecnes
            if (next_node := node.next):
                next_node.prev = node.prev
            if (prev_node := node.prev):
                prev_node.next = node.next
            break


    def append(self, data) -> None:
        new_node = Node(data)
        if not self.head:
            self.current = new_node
            self.head = new_node

        else:
            cur = self.head
            while cur.prev:
                cur = cur.prev
            cur.prev = new_node

    def prepend(self, data) -> None:
        new_node = Node(data)
        if (old_head := self.head):
            self.head = new_node
            self.head.prev = old_head
            old_head.next = self.head

        else:
            self.current = new_node
            self.head = self.tail = new_node

    def get_next(self) -> parse_tex.Flashcard:
        # Current node exists and has next reference, then return next reference and set current to next
        if self.current and self.current.next:
            self.current = self.current.next
            return self.current.data
        else:
            raise FlashcardNotFoundException("Already at the end of the flashcards") # TODO - dont have a fucking clue why I wrote TODO... better exception message? maybe...

    def get_prev(self) -> parse_tex.Flashcard:
        if self.current and self.current.prev:
            self.current = self.current.prev
            return self.current.data
        else:
            raise FlashcardNotFoundException("Already at the begging of the flashcards")

    def _get_last_node(self):
        current = self.head
        while current and current.prev:
            current = current.prev
        return current

    def __iter__(self):
        """ [head -> head.prev -> ... -> head.prev.(...).prev] """
        current = self.head
        while current:
            yield current.data
            current = current.prev

    def __len__(self) -> int:
        counter = 0
        for _ in self:
            counter += 1
        return counter

    def __reversed__(self):
        """ [head <- last.next.(...).next <- ... <- last.next <- last] """
        current = self._get_last_node()
        while current:
            yield current.data
            current = current.next


class TexCompilationManager:
    """ Handles compilation of latex and caching process """

    def __init__(self, cache_dir: str ="cache_tex", cache_size: int =50) -> None:
        """
        -- Params --
        # TODO: Make cache_dir full path and depend on project config
        cache_dir: location of cache directory. ie where should pdf_files be saved
        cache_size: limit on number of files allowed in cache_dir. Oldest files are deleted from cache first
        """
        self.cache_dir: Path = Path(__file__).parent / cache_dir
        self.cache_size = cache_size
        self.cache: dict = self._load_cache()

        if not self.cache_dir.is_dir():
            logger.debug(f"{self.cache_dir} does not exists, creating {self.cache_dir}")
            self.cache_dir.mkdir()

    def _load_cache(self) -> dict:
        return dict()

    @staticmethod
    def get_hash(tex: str, hash_length=8) -> str:
        """ Figure out the probablity of colllision.
        Should also figure out which hash algortithm I am using and which I should be using """
        hash = hashlib.sha256(tex.encode('utf-8')).hexdigest()
        trucated_hash = hash[:hash_length]
        return trucated_hash

    @staticmethod
    def latex_template(tex: str) -> str:
        return fr"""
\documentclass[preview]{{standalone}}
\usepackage{{amsmath,amsfonts,amsthm,amssymb,mathtools}}
\begin{{document}}
{tex}
\end{{document}}"""

    def compile_card(self, card: parse_tex.Flashcard) -> None:
        """ Attemps to compile flashcard question and answer tex. If compilation fails, card.error_message is set"""
        # Check for cards that have already beet catagorized as invalid
        if card.error_message:
            logger.debug(f"Card: {card} contains error message, aborting compilation process")
            return None

        card.pdf_question_path = self.compile_latex(str(card.question)) # most likley does not need to be converted to str... to lazy to test
        card.pdf_answer_path = self.compile_latex(str(card.answer))

        # If compilation fails set relavent error message
        # This seems sorta useless...
        if not card.pdf_question_path:
            card.error_message = f"Could not compile question: {card.question}"
        if not card.pdf_answer_path:
            card.error_message += f"Could not compile answer: {card.answer}"


    def compile_latex(self, tex: str) -> str | None:
        """ Attempts to compile latex string
        -- Params --
        tex: string containig latex code
        returns: path to compiled pdf or None if compilation fails
        """
        tex = tex.replace('\n', ' ')
        tex_hash = self.get_hash(tex)

        with tempfile.TemporaryDirectory() as tmpdir:
            tex_file_path = Path(tmpdir) / "temp.tex"
            pdf_file_path = Path(tmpdir) / "temp.pdf"
            tex_file_path.write_text(self.latex_template(tex), encoding='utf-8')


            cmd = ['pdflatex', '-interaction=nonstopmode', '-output-directory', str(tmpdir), str(tex_file_path)]
            logger.info(f"Running command {' '.join(cmd)}")
            result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
            # Command did not run successfully
            if result.returncode != 0:
                logger.error(f"Failed to run {' '.join(cmd)}. Tex file contents: {tex}, stderr={result.stderr}")
                return None
            logger.info(f"Successfully ran {' '.join(cmd)}. Tex file contents: {tex}")
            new_path = pdf_file_path.rename(self.cache_dir / f"{tex_hash}.pdf")
        return str(new_path)

class FlashcardModel:
    """ Acts as a container for the flashcard data. MVC architecture for gui """

    def __init__(self, compiler: TexCompilationManager) -> None:
        """
        -- Params --
        compiler: manages compilation of flash cards, type TexCompilationManager
        """
        self.compiler = compiler
        self.flashcards: list[parse_tex.Flashcard] = []
        self.compiled_flashcards: FlashcardDoubleLinkedList = FlashcardDoubleLinkedList()
        self.flashcard_lock = threading.RLock()
        self.thread_stop_event = threading.Event()
        self.current_card = None
        self.compile_thread = StoppableThread(callback=self._compile)

    def _load_macros(self) -> dict:
        """ Load macros from file used as macros package in tex document """
        return parse_tex.load_macros(parse_tex.MACRO_PATH, parse_tex.MACRO_NAMES)

    def _next_compiled_flashcard(self) -> parse_tex.Flashcard:
        """ Thread safe retreival of next card  """
        with self.flashcard_lock:
            next_card = self.compiled_flashcards.get_next()
            self.current_card = next_card
            self.current_card.seen = True
            return next_card

    def remove_flashcard(self, card: parse_tex.Flashcard):
        pass

    def _prev_compiled_flashcard(self) -> parse_tex.Flashcard:
        """ Thread safe retreival of previous card  """
        with self.flashcard_lock:
            prev_card = self.compiled_flashcards.get_prev()
            self.current_card = prev_card
            self.current_card.seen = True
            return prev_card

    def _prepend_compiled_flashcard(self, card) -> None:
        """ Thread safe prepend to FlashcardDoubleLinkedList """
        with self.flashcard_lock:
            self.compiled_flashcards.prepend(card)

    def _append_compiled_flashcard(self, card) -> None:
        """ Thread safe append to FlashcardDoubleLinkedList """
        with self.flashcard_lock:
            self.compiled_flashcards.append(card)

    def load_flashcards(self, section_names: list[str], paths: list[Path], start_compilation=True) -> None:
        r""" Load flash cards with raw tex
        -- Params --
        section_names: names of box's defined by user. ie
        \defin{Integer}{Content} is a section called 'defin'
        """
        logger.info(f"Calling load_flashcards(section_names={section_names}, paths={paths}, start_compilation={start_compilation})")

        get_data_stage = parse_tex.GetDataStage(paths)
        clean_data_stage = parse_tex.CleanStage(self._load_macros())
        filter_and_make_flashcards_stage = parse_tex.FilterBySectionAndMakeFlashcardsStage(section_names)
        pipeline = parse_tex.FlashcardsPipeline([
            get_data_stage, clean_data_stage, filter_and_make_flashcards_stage
            ])
        flash_cards = pipeline.run()
        if flash_cards:
            random.shuffle(flash_cards)

        self.flashcards = flash_cards
        logger.debug(f"Loaded flashcards: {self.flashcards}")
        self.compiled_flashcards = FlashcardDoubleLinkedList() # Should I delete old list?

#        if start_compilation:
#            logger.info("Starting FlashCardModel compile thread")
#            self.compile_thread.start()

    def next_flashcard(self) -> parse_tex.Flashcard:
        """ Retreive next flashcard, implements blocking behaviour when there are no compiled cards however one is currently being compiled """
        # If there is a flash card with compiled latex return that card
        while self.flashcards and (not self.compiled_flashcards.current or not self.compiled_flashcards.current.next):

            logger.debug(f"{self.next_flashcard} waiting on conditions self.flashcards and (not self.compiled_flashcards or not self.compiled_flashcards.current.next)")
            time.sleep(1)
        return self._next_compiled_flashcard()


    def prev_flashcard(self) -> parse_tex.Flashcard:
        """ Should I implement empty card or return None """
        return self._prev_compiled_flashcard()

    def _count_precompiled_cards(self):
        """ Returns number of compiled cards that are 'next' and have not been viewed in the FlashcardDoubleLinkedList """
        counter = 0
        card = None if self.compiled_flashcards.current is None else self.compiled_flashcards.current.next
        while card and not card.data.seen:
            card = card.next
            counter+=1

        return counter

    def _compile(self, event: threading.Event, compile_num=2):
        logger.debug(f"Calling {self._compile}(event={event}, compile_num={compile_num})")
        while self._count_precompiled_cards() > compile_num or len(self.flashcards) == 0:
            logger.debug(f"_compile waiting for len(self.compiled_flashcards)= {len(self.compiled_flashcards)} < {compile_num}=compiled_num or len(flashcards)={len(self.flashcards)} == 0")
            if event.is_set():
               break

            time.sleep(1)

        with self.flashcard_lock:
            if not self.flashcards:
                return

            card = self.flashcards.pop()
            try:
                self.compiler.compile_card(card)
                logger.debug(f"Compiled card: {card}")
                self._prepend_compiled_flashcard(card)

            except Exception as e:
                logger.error(f"Failed to compile {e}")
