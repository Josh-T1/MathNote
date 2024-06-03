from os.path import isdir
import random
from re import L
import threading
import tempfile
from pathlib import Path
import time
import sys
import os
import subprocess
import hashlib
from ..Course import parse_tex
"""
Figure out a method for cashing results so that I do not need parse latex files everytime
"""


#MACROS = parse_tex.load_macros()
class TexCompilationManager:

    def __init__(self, cache_dir: str ="cache_tex", cache_size: int =50) -> None:
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

    def compile_card(self, card: parse_tex.FlashCard):
        # Make a system for displaying flashcard info
        compiled_question_path = self.compile_latex(card.question) or "Error"
        compiled_answer_path = self.compile_latex(card.answer) or "Error"
        card.question = compiled_question_path
        card.answer = compiled_answer_path

    def compile_latex(self, tex: str):
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

            pdf_file_path.rename(self.cache_dir / f"{tex_hash}.pdf")
        return pdf_file_path
"""
What should empty card look like and how should I display plain text?
"""
class FlashcardModel:
    def __init__(self, file_paths: list[Path], compiler ,compile: int = 5) -> None:
        self.compiler = compiler
        self.file_paths = file_paths
        self.flashcards: list[parse_tex.FlashCard] = []
        self.compiled_flashcards: list[parse_tex.FlashCard] = []
        self.viewed_cards: list[parse_tex.FlashCard] = []
        self.currently_compiling: bool = False
        self.compile = compile
        self.flashcard_lock = threading.Lock()
        self.compile_thread = threading.Thread(target=self._compile)

    def _load_macros(self):
        return parse_tex.load_macros(parse_tex.MACRO_PATH, parse_tex.MACRO_NAMES)

    def _get_compiled_flash_card(self):
        with self.flashcard_lock:
            if self.compiled_flashcards:
                return self.compiled_flashcards.pop()
        return None

    def _append_compiled_flash_card(self, card):
        with self.flashcard_lock:
            self.compiled_flashcards.append(card)

    def load_flashcards(self, section_names: list[str]):
        """ Load flash cards with raw tex """
        get_data_stage = parse_tex.GetDataStage(self.file_paths)
        clean_data_stage = parse_tex.CleanStage(self._load_macros())
        filter_and_make_flashcards_stage = parse_tex.FilterBySectionAndMakeFlashcardsStage(section_names)
        pipeline = parse_tex.FlashcardsPipeline([
            get_data_stage, clean_data_stage, filter_and_make_flashcards_stage
            ])
        flash_cards = pipeline.run()
        if flash_cards:
            random.shuffle(flash_cards)
        self.flashcards = flash_cards

    def next_flashcard(self) -> parse_tex.FlashCard:
        """  """
        # If there is a flash card with compiled latex return that card
        card = self._get_compiled_flash_card()

        # Wait untill next card is compiled
        while self.flashcards and not card:
            card = self._get_compiled_flash_card()
            time.sleep(0.1)

        if card:
            return card

        # There are no compiled cards and no compilation in process. Only possiblility is there are no cards or issue with thread
        return parse_tex.EmptyFlashCard("Empty")

    def prev_flashcard(self) -> parse_tex.FlashCard:
        """ Should I implement empty card or return None """
        if not self.viewed_cards:
            return parse_tex.EmptyFlashCard("Empty")
        card = self.viewed_cards.pop(-1)
        self.viewed_cards.append(card)
        return card

    def _compile(self):
        while True:
            while len(self.compiled_flashcards) > 5 or len(self.flashcards) == 0:
                time.sleep(1)

            card = self.flashcards.pop()
            compiled_card = self.compiler.compile_card(card)
            self._append_compiled_flash_card(compiled_card)


if __name__ == '__main__':
    path = Path("/Users/joshuataylor/documents/notes/uofc/math-445/lectures/lec_03.tex")
    manager = TexCompilationManager()
    model = FlashcardModel([path],manager)
    model.load_flashcards(['defin'])
    card = model.flashcards[0]

#    print(manager.latex_template(card.answer))
    res = manager.compile_latex(card.answer)
    print(res)
#    manager.compile_card()
