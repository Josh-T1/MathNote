from pathlib import Path
import logging
from typing import OrderedDict
import hashlib
import subprocess
import tempfile

from ..models import TrackedText, Flashcard, SectionNames
from .._enums import FileType


logger = logging.getLogger(__name__)


class CompilationManager:
    """ Handles compilation of latex, flashcard cache, and formating of flashcard."""

    def __init__(self, cache_root: str ="cache_tex", cache_size: int = 200) -> None:
        """
        -- Params --
        cache_root: location of cache directory
        cache_size: limit on number of files allowed in cache_dir. Oldest files are deleted from cache first
        """
        self._ignore_hashes = ["empty"]
        self.cache_root = Path(__file__).resolve().parent / cache_root
        self.cache_dir = self.cache_root / "pdf"
        self.cache_size = cache_size + len(self._ignore_hashes) # Ignore cached files for default messages
        self._cache: dict[str, str] = {}


        if not self.cache_root.is_dir():
            logger.debug(f"{self.cache_root} does not exists. Creating directory...")
            self.cache_root.mkdir()
        if not self.cache_dir.is_dir():
            logger.debug(f"{self.cache_dir} does not exists. Creating directory...")
            self.cache_dir.mkdir()

    @property
    def cache(self) -> dict[str, str]:
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

    def list_cache_by_oldest(self) -> OrderedDict[str, Path]:
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

    def compile_card(self, card: Flashcard) -> None:
        """ Attemps to compile flashcard question/answer latex. If compilation fails """
        compile_func = self.compile_latex if card.question.filetype() == FileType.LaTeX else self.compile_typst # TODO not handling Unsupported note typst. Catch earlier
        card.pdf_question_path = compile_func(card.question)
        card.pdf_answer_path = compile_func(card.answer)

        for member_name, content in card.additional_info.items():
            if SectionNames.is_name(member_name):
                path = compile_func(content)
                setattr(card, f"pdf_{member_name}_path", path)
                setattr(card, f"{member_name}", content)

        self._format_card(card)

    def _format_card(self, card: Flashcard):
        """ If card has a blank question section or its question is equal to the theorem number
        replace question with 'answer' field (answer in this case is the theorem statement) and
        replace answer with proof """
        if hasattr(card, SectionNames.PROOF.name) and hasattr(card, SectionNames.PROOF.name):
            if len(card.question) == 0 or not any(char.isalpha() for char in card.question):
                prefix = card.question if card.question else None
                card.question = card.answer
                card.pdf_question_path = card.pdf_answer_path
                if prefix is not None:
                    card.answer = prefix + getattr(card, SectionNames.PROOF.name)
                else:
                    card.answer = getattr(card, SectionNames.PROOF.name)
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

    def compile_latex(self, tex: TrackedText) -> str | None:

        """ Attempts to compile latex string
        -- Params --
        tex: string containig latex code
        returns: path to compiled pdf or None if compilation fails
        """
        source = tex.source
        tex_str = str(tex)
        tex_hash = "empty" if not tex_str else self.get_hash(tex_str)
        if tex_hash in self.cache.keys():
            logger.debug(f"Getting file {tex_hash} from cache")
            return self.cache[tex_hash]

        with tempfile.TemporaryDirectory() as tmpdir:
            tex_file_path = Path(tmpdir) / "temp.tex"
            pdf_file_path = Path(tmpdir) / "temp.pdf"
            tex_file_path.write_text(latex_template(tex_str), encoding='utf-8')



            cmd = ['latexmk', "-f", '-pdflatex=pdflatex -interaction=nonstopmode', f'-output-directory={str(tmpdir)}',"-pdf", str(tex_file_path)]
            logger.debug(f"Attempting to compile card")
            result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
            # Command did not run successfully
            if result.returncode != 0:
                logger.error(f"Error running {' '.join(cmd)}. Tex file contents: {tex_str}, stderr={result.stderr}\nSource={source}")

                if not pdf_file_path.is_file(): # Error != no pdf produced
                    return None

            logger.info(f"Successfully generated pdf")
            new_path = pdf_file_path.rename(self.cache_dir / f"{tex_hash}.pdf").resolve()

        return str(new_path)

    # TODO use source File for typst_file_path?
    # TODO refactor this and compile latex
    def compile_typst(self, typst: TrackedText) -> str | None:
        """ Compile typst string
        -- Params --
        tex: string containig latex code
        returns: path to compiled pdf or None if compilation fails
        """
        # TODO: I dont think cache is working properly
        source = typst.source
        if source is None:
            return #TODO fix this

        typst_str = str(typst)
        typst_hash = "empty" if not typst_str else self.get_hash(typst_str)

        if typst_hash in self.cache.keys():
            logger.debug(f"Getting file {typst_hash} from cache")
            return self.cache[typst_hash]

        with tempfile.TemporaryDirectory() as tmpdir:
            typst_file_path = Path(tmpdir) / "temp.typ"
            pdf_file_path = Path(tmpdir) / "temp.pdf"
            typst_file_path.write_text(typst_template(typst_str), encoding='utf-8')


            cmd = ['typst','compile', "--format", "pdf", str(typst_file_path)]
            logger.debug(f"Attempting to compile card")
            result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                    )
            # Command did not run successfully
            if result.returncode != 0:
                logger.error(f"Error running {' '.join(cmd)}. Tex file contents: {typst_str}, stderr={result.stderr}\nSource={source}")

                if not pdf_file_path.is_file(): # Error != no pdf produced
                    return None
            logger.info(f"Successfully generated pdf")
            new_path = pdf_file_path.rename(self.cache_dir / f"{typst_hash}.pdf").resolve()

        return str(new_path)

