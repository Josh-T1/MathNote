from pathlib import Path
import logging
from typing import OrderedDict
import hashlib
import tempfile

from mathnotelib.models.source_file import SourceFile

from .compiler import CompileOptions, compile_source, latex_template, typst_template
from ..models import TrackedText, Flashcard, SectionNames
from .._enums import FileType, OutputFormat


logger = logging.getLogger(__name__)


class CompilationManager:
    """ Handles compilation of 'code' """

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
        self.cache: dict[str, str] = self._load_cache()


        if not self.cache_root.is_dir():
            logger.debug(f"{self.cache_root} does not exists. Creating directory...")
            self.cache_root.mkdir()
        if not self.cache_dir.is_dir():
            logger.debug(f"{self.cache_dir} does not exists. Creating directory...")
            self.cache_dir.mkdir()


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
        card.pdf_question_path = self.compile(card.question)
        card.pdf_answer_path = self.compile(card.answer)

        for member_name, content in card.additional_info.items():
            if SectionNames.is_name(member_name):
                path = self.compile(content)
                setattr(card, f"pdf_{member_name}_path", path)
                setattr(card, f"{member_name}", content)
        self._format_card(card)

    def _format_card(self, card: Flashcard):
        """ If card has a blank question section or its question is equal to the theorem number
        replace question with 'answer' field (answer in this case is the theorem statement) and
        replace answer with proof """
        has_alpha = any(char.isalpha() for char in card.question)
        has_proof = hasattr(card, SectionNames.PROOF.name)
        if (len(card.question) == 0 or not has_alpha) and has_proof:
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

    def compile(self, text: TrackedText):
        source = text.source
        if source is None: # TODO should never be NOne, check this
            print("TODO: should not be None")
            return
        if text.filetype() == FileType.LaTeX:
            ext = ".tex"
            template_func = latex_template
        else:
            ext = ".typ"
            template_func = typst_template
        string = str(text)
        str_hash = "emtpy" if not string else self.get_hash(string)
        if str_hash in self.cache.keys():
            logger.debug(f"Getting file {str_hash} from cache")
            return self.cache[str_hash]

        with tempfile.TemporaryDirectory() as tmpdir:
            source_file_path = Path(tmpdir) / f"temp{ext}"
            pdf_file_path = Path(tmpdir) / "temp.pdf"
            source_file_path.write_text(template_func(string), encoding='utf-8')
            file = SourceFile(source_file_path)
            options = CompileOptions(source_file_path, OutputFormat.PDF)
            return_code = compile_source(file, options)
            if return_code == 1:
                logger.error(f"Compilation error, file contents: {string}\nSource={source}")
                return

            if not pdf_file_path.is_file(): # Error != no pdf produced
                    return None

            logger.info(f"Successfully generated pdf")
            new_path = pdf_file_path.rename(self.cache_dir / f"{str_hash}.pdf").resolve()
        return str(new_path)
