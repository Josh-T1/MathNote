import random
import threading
import tempfile
from pathlib import Path
import time
import subprocess
import hashlib
from ..course import parse_tex
import logging


"""
Figure out a method for cashing results so that I do not need parse latex files everytime
"""
class FlashcardNotFoundException(Exception):
    pass

class StoppableThread(threading.Thread):
    """ This is some proper fuckery and poor class naming. The target function for the thread needs access to FlashcardModel properties. In order to
    de couple StoppableThread and FlashcardModel we accept a callback that is called by StoppableThread.run() on every loop for which the _stop_event
    is not set. The issue is that this specific callback requires access to StoppableThread._stop_event which requires us to pass self._stop_event
    to callback. This works however it hardly makes sense to only accept callbacks that accept ._stop_event in the general 'StoppableThread'
    class... What about a CompileTexThread that implements FlashcardModel specific logic?...that solution also sucks
    """
    def __init__(self, *args, **kwargs):
        self._stop_event = threading.Event()
        self._stopped_properly = threading.Event()
        self.inner_target = kwargs.get("callback")
        del kwargs["callback"]
        kwargs["target"] = self.run
        super().__init__(*args, **kwargs)

    def stopped(self) -> bool:
        return self._stop_event.is_set()

    def run(self):
        while not self.stopped():
            if self.inner_target:
                self.inner_target(self._stop_event)
        self._stopped_properly.set()

    def wait_for_stop(self):
        """ waits for stop event and resets events """
        self._stopped_properly.wait()

    def reset_events(self):
        self._stop_event.clear()
        self._stopped_properly.clear()

    def stop(self):
        self._stop_event.set()

class Node:
    def __init__(self, data) -> None:
        self.data = data
        self.next: Node | None = None
        self.prev: Node | None = None

class FlashcardDoubleLinkedList:
    def __init__(self) -> None:
        self.head = None
        self.current = None


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
            raise FlashcardNotFoundException("Already at the end of the flashcards") # TODO

    def get_prev(self) -> parse_tex.Flashcard:
        if self.current and self.current.prev:
            self.current = self.current.prev
            return self.current.data
        else:
            raise FlashcardNotFoundException("Already at the begging of the flashcards")

    def __len__(self) -> int:
        counter = 0
        if not self.head:
            return counter
        cur = self.head
        while cur.prev:
            cur = cur.prev
            counter += 1
        return counter

#MACROS = parse_tex.load_macros()
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
            self.cache_dir.mkdir()

    def _load_cache(self) -> dict:
        return dict()

    @staticmethod
    def get_hash(tex: str, hash_length=8) -> str:
        """ figure out the probablity of colllision. Should also figure out which hash algortithm I am using and which I should be using """
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
            return None

        compiled_question_path = self.compile_latex(card.question)
        compiled_answer_path = self.compile_latex(card.answer)

        # If compilation fails set relavent error message
        if not compiled_question_path:
            card.error_message = f"Could not compile question: {card.question}"
        if not compiled_answer_path:
            card.error_message += f"Could not compile question: {card.answer}"

        # If compilation fails fallback on raw tex otherwise set to path of pdf
        card.question = compiled_question_path or card.question
        card.answer = compiled_answer_path or card.answer

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

            result = subprocess.run(
                    ['pdflatex', '-interaction=nonstopmode', '-output-directory', str(tmpdir), tex_file_path],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
            # Command did not run successfully
            if result.returncode != 0:
                return None

            new_path = pdf_file_path.rename(self.cache_dir / f"{tex_hash}.pdf")
        return str(new_path)
"""
What should empty card look like and how should I display plain text?
"""

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
            return next_card

    def _prev_compiled_flashcard(self) -> parse_tex.Flashcard:
        """ Thread safe retreival of previous card  """
        with self.flashcard_lock:
            prev_card = self.compiled_flashcards.get_prev()
            self.current_card = prev_card
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
        if not self.compile_thread.stopped():
            self.compile_thread.stop()
            self.compile_thread.wait_for_stop()
            self.compile_thread.reset_events()

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
        self.compiled_flashcards = FlashcardDoubleLinkedList() # Should I delete old list?

        if start_compilation:
            self.compile_thread.run()

    def next_flashcard(self) -> parse_tex.Flashcard:
        """ Retreive next flashcard, implements blocking behaviour when there are no compiled cards however one is currently being compiled """
        # If there is a flash card with compiled latex return that card
        while self.flashcards and (not self.compiled_flashcards.current or not self.compiled_flashcards.current.next):
            time.sleep(1)
        return self._next_compiled_flashcard()


    def prev_flashcard(self) -> parse_tex.Flashcard:
        """ Should I implement empty card or return None """
        return self._prev_compiled_flashcard()

    def _compile(self, event: threading.Event, compile_num=2):
        while len(self.compiled_flashcards) > compile_num or len(self.flashcards) == 0:

            if event.is_set():
               break

            time.sleep(1)

        if not self.flashcards:
            return

        card = self.flashcards[-1]
        with self.flashcard_lock:
            card = self.flashcards.pop()
            self.compiler.compile_card(card)
            self._prepend_compiled_flashcard(card)


if __name__ == '__main__':
    pass
#    path = Path("/Users/joshuataylor/documents/notes/uofc/math-445/lectures/lec_03.tex")
#    manager = TexCompilationManager()
#    model = FlashcardModel([path],manager)
#    model.load_flashcards(['defin'])
#    card = model.next_flashcard()
#
#    res = manager.compile_latex(card.answer)
#    print(str(res))
#    app = QApplication([])
#    window = MainWindow()
#    window.plot_tex(str(res))
#    window.show()
#    app.exec()
