import random
import threading
import tempfile
from pathlib import Path
import time
import subprocess
import hashlib
from typing import OrderedDict, Deque
from ..course import parse_tex
import logging
from collections import deque
from ..utils import SectionNames, SectionNamesDescriptor, config
from .edit_tex import latex_template

logger = logging.getLogger("flashcard")


class FlashcardNotFoundException(Exception):
    pass

class StoppableThread(threading.Thread):
    """
    Accepts kwarg 'callback' of type Callable that is called by StoppableThread._run() on every loop for which the _stop_event
    is not set. The callback must accept one parameter: threading.Event(). If the callback implements its own blocking behaviour it must
    break out of that state when even it set (see FlashcardModel._compile)
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

class Node:
    def __init__(self, data) -> None:
        self.data = data
        self.next: Node | None = None
        self.prev: Node | None = None

class FlashcardDoubleLinkedList:
    """ Container for Flashcards """
    def __init__(self, *args) -> None:
        self.head = None
        self.current = None
        for arg in args:
            self.append(arg)

    def clear(self):
        self.head = None
        self.current = None

    def remove(self, index: int):
        """ Remove node at index """
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
    """ Handles compilation of latex, flashcard cache, and formating of flashcard."""

    def __init__(self, cache_dir: str ="cache_tex", cache_size: int = 200) -> None:
        """
        -- Params --
        cache_dir: location of cache directory. ie where should pdf_files be saved
        cache_size: limit on number of files allowed in cache_dir. Oldest files are deleted from cache first
        """
        self._ignore_hashes = ["empty"]
        self.cache_dir: Path = Path(__file__).resolve().parent / cache_dir / "pdf"
        self.cache_size = cache_size + len(self._ignore_hashes) # Ignore cached files for default messages
        self._cache: dict = {}


        if not self.cache_dir.is_dir():
            logger.debug(f"{self.cache_dir} does not exists, creating {self.cache_dir}")
            self.cache_dir.mkdir()

    @property
    def cache(self):
        if not self._cache:
            self._cache = self._load_cache()
        return self._cache

    def _load_cache(self) -> dict:
        """
        returns: dictionary with key value pairs {filename: path_to_file}, where all files are in self.cache_dir. Filenames
                 are the truncated hash values for their respective raw latex contents
        """
        cache = {}
        for file in self.cache_dir.iterdir():
            if file.is_file():
                cache[file.name] = str(file)
        return cache

    def list_cache_by_oldest(self):
        """ List cached files by oldest edit ignoring cached files for default messages """
        cache_paths = {hash: Path(filepath) for hash, filepath in self.cache.items() if hash + ".pdf" not in self._ignore_hashes}
        cache_paths_sorted = OrderedDict(sorted(cache_paths.items(), key=lambda item_pair: item_pair[1].stat().st_mtime, reverse=True))
        return cache_paths_sorted

    @staticmethod
    def get_hash(tex: str, hash_length: int = 8) -> str:
        """ Gets has value of tex and returns truncated has
        TODO: Figure out the probablity of colllision.

        -- Params --
        hash_length: has will be truncated to satisfy len(hash_truncated) = hash_length
        tex: string containing latex
        """
        hash = hashlib.sha256(tex.encode('utf-8')).hexdigest()
        trucated_hash = hash[:hash_length]
        return trucated_hash

    def compile_card(self, card: parse_tex.Flashcard) -> None:
        """ Attemps to compile flashcard question/answer latex. If compilation fails """
        card.pdf_question_path = self.compile_latex(card.question) # str needed to convert TrackedString -> str for hash value
        card.pdf_answer_path = self.compile_latex(card.answer)

        for member_name, content in card.additional_info.items():
            if SectionNames.is_name(member_name):
                path = self.compile_latex(content)
                setattr(card, f"pdf_{member_name}_path", path)
                setattr(card, f"{member_name}", content)

        self._format_card(card)

    def _format_card(self, card: parse_tex.Flashcard):
        """ If card has a blank question section or its question is equal to the theorem number
        replace question with 'answer' field (answer in this case is the theorem statement) and
        replace answer with proof """
        if hasattr(card, SectionNames.PROOF.name) and hasattr(card, SectionNames.PROOF.name):
            if len(card.question) == 0 or not any(char.isalpha() for char in card.question):
                prefix = f"({card.question})" if card.question else ""
                card.question = card.answer
                card.pdf_question_path = card.pdf_answer_path
                card.answer = prefix + getattr(card, SectionNames.PROOF.name)
                card.pdf_answer_path = getattr(card, f"pdf_{SectionNames.PROOF.name}_path")
                delattr(card, SectionNames.PROOF.name)
                delattr(card, f"pdf_{SectionNames.PROOF.name}_path")

    def add_to_cache(self, file_path: Path) -> None:
        """ Add new file to cache
        -- Params --
        file_path: Path object of file begin added to cache
        """
        self.cache[file_path.name] = str(file_path)

    def remove_from_cache(self, filepath: Path):
        del self.cache[filepath.name]
        filepath.unlink()

    def compile_latex(self, tex: parse_tex.TrackedString) -> str | None:

        """ Attempts to compile latex string
        -- Params --
        tex: string containig latex code
        returns: path to compiled pdf or None if compilation fails
        """
        source = tex.source_history.root
        tex_str = str(tex)
        tex_hash = "empty" if not tex_str else self.get_hash(tex_str)
        if tex_hash in self.cache.keys():
            logger.debug(f"Getting file {tex_hash} from cache")
            return self.cache[tex_hash]

        with tempfile.TemporaryDirectory() as tmpdir:
            tex_file_path = Path(tmpdir) / "temp.tex"
            pdf_file_path = Path(tmpdir) / "temp.pdf"
            tex_file_path.write_text(latex_template(tex_str), encoding='utf-8')



            cmd = ['latexmk',
                   '-pdflatex=pdflatex -interaction=nonstopmode', f'-output-directory={str(tmpdir)}',"-pdf", str(tex_file_path)]
            #cmd = ['pdflatex', '-interaction=nonstopmode', '-output-directory', str(tmpdir), str(tex_file_path)]
            logger.debug(f"Attempting to compile card")
            result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
            # Command did not run successfully
            if result.returncode != 0:
                logger.error(f"Failed to run {' '.join(cmd)}. Tex file contents: {tex_str}, stderr={result.stderr}\nSource={source}")
                return None

            logger.info(f"Successfully compiled card")
            new_path = pdf_file_path.rename(self.cache_dir / f"{tex_hash}.pdf").resolve()

        return str(new_path)

class FlashcardModel:
    """ Acts as a container for the flashcard data. MVC architecture for gui """

    def __init__(self, compiler: TexCompilationManager) -> None:
        """
        -- Params --
        compiler: manages compilation of flash cards, type TexCompilationManager
        """
        self.cache_dir = Path(__file__).parent.resolve() / "cache_dir"
        self.compiler = compiler
        self.flashcards: Deque[parse_tex.Flashcard] = deque()
        self.flashcard_cache = parse_tex.FlashcardCache(self.cache_dir / "flashcards")
        self.compiled_flashcards: FlashcardDoubleLinkedList = FlashcardDoubleLinkedList()
        self.flashcard_lock = threading.RLock()
        self.thread_stop_event = threading.Event()
        self.current_card = None # threadsafe, never accessed by thread
        self.compile_thread = StoppableThread(callback=self._compile)
        self._macros = None

    @property
    def macros(self) -> dict:
        r"""
        returns the user defined 'macros' that have the form \newcommand[1]{...}{...} that are usually located in macros.tex
        (parse_tex.py has limited parsing capabilities)
        """
        if self._macros is None:
            self._macros = self._load_macros()
        return self._macros

    def _load_macros(self) -> dict:
        """ Load macros from MACRO_PATH. Note there are limitations on macros that parse_tex can load and MACRO_NAMES are not created dynamically...See parse_tex.py """
        return parse_tex.load_macros(parse_tex.MACRO_PATH, parse_tex.MACRO_NAMES)


    def _next_compiled_flashcard(self) -> parse_tex.Flashcard:
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

    def load_flashcards(self, section_names: list[SectionNamesDescriptor], paths: list[Path], shuffle=True) -> None:
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

        data_iterable = parse_tex.TexDataGenerator(paths)
        # TODO fix get_hack_macros
        clean_data_stage = parse_tex.CleanStage(self.macros | parse_tex.get_hack_macros())
        filter_and_build_flashcards = parse_tex.FlashcardBuilder(parse_tex.MainSectionFinder(section_names))

        filter_and_build_flashcards.add_subsection_finder(parse_tex.ProofSectionFinder(
            SectionNames.PROOF, [SectionNames.THEOREM, SectionNames.PROPOSITION, SectionNames.LEMMA, SectionNames.COROLLARY]) #type: ignore __getattr__ returns SectionNamesDescriptor not str
                                                              )
        pipeline = parse_tex.FlashcardsPipeline(data_iterable, filter_and_build_flashcards, [clean_data_stage])

        for flash_cards in pipeline:
            if shuffle:
                random.shuffle(flash_cards)
            with self.flashcard_lock:
                for flashcard in flash_cards:
                    self.flashcards.append(flashcard)
            logger.debug(f"Loaded flashcards: {flash_cards}")

    def next_flashcard(self) -> parse_tex.Flashcard:
        """ Retreive next flashcard, implements blocking behaviour when there are no compiled cards however one is currently being compiled """
        # If there is a flash card with compiled latex return that card
        while len(self.flashcards) != 0 and (not self.compiled_flashcards.current or not self.compiled_flashcards.current.next):
            logger.debug(f"{repr(self.next_flashcard)} waiting on conditions self.flashcards and (not self.compiled_flashcards or not self.compiled_flashcards.current.next)")
            time.sleep(1)
        return self._next_compiled_flashcard()

    def prev_flashcard(self) -> parse_tex.Flashcard:
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
        for card in self.compiled_flashcards:
            if card.pdf_answer_path:
                paths.append(card.pdf_answer_path)
            if card.pdf_question_path:
                paths.append(card.pdf_question_path)
        return paths

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

            # Logic block for 'cleaning' cache
            delete_num = len(self.compiler.cache) - self.compiler.cache_size
            if delete_num <= 0:
                return

            cached_paths = self.compiler.list_cache_by_oldest()
            flashcard_hash = (set(self.compiler.get_hash(flashcard.question) for flashcard in self.flashcards)
                              | set(self.compiler.get_hash(value) for _card in self.flashcards for value in _card.additional_info.values()))

            # delete cached file starting from oldest if hash(flashcards.question) != hash(cached file)
            while delete_num > 0 and len(cached_paths) > 0:
                hash, filepath = cached_paths.popitem(last=True)
                if hash not in flashcard_hash:
                    logger.debug(f"Removing cached file: {filepath}")
                    self.compiler.remove_from_cache(filepath)
                    delete_num -= 1

            return None
