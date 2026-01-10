from pathlib import Path
import logging
from typing import OrderedDict
import hashlib
import tempfile

from ..models import SourceFile

from .compiler import CompileOptions, compile_source
from ..models import TrackedText, Flashcard
from .._enums import FileType, OutputFormat


logger = logging.getLogger(__name__)


# TODO make package dynamic
def latex_template(tex: str) -> str:
    """ Flashcard contents are compiled with the following template """
    return fr"""
\documentclass[preview, border=0.1in]{{standalone}}
\usepackage{{amsmath,amsfonts,amsthm,amssymb,mathtools}}
\usepackage{{mathrsfs}}

\begin{{document}}
{tex}
\end{{document}}"""

# TODO make package dynamic
def typst_template(typ: str, packages: list[dict[str, list[str]]] | None = None) -> str:
    return fr"""
#set page(
        width: 14cm,
        height: auto,
        margin: 5pt
        )
#import "@local/notes:1.0.0": *

{typ}
"""

# Make config so that it tracks cache dir
# Then we make dir in command not obj
class FlashcardCache:
    def __init__(self, cache_dir: Path, cache_size: int=200):
        super().__init__()
        self.cache_root = cache_dir
        self.cache_pdf = self.cache_root / "pdf"
        self.cache_size = cache_size
        self._cache: dict[str, Path] = self._load_cache()
        self._section_names: list[str] = []
        self._ignore_hashes = {"empty"} # TODO

        if not self.cache_root.is_dir():
            msg = f"{self.cache_root} does not exists"
            logger.error(msg)
            raise EnvironmentError(msg)
        if not (self.cache_root / "pdf").is_dir():
            msg = f"{self.cache_root / "pdf"} does not exists"
            logger.error(msg)
            raise EnvironmentError(msg)

    def cleanup_cache(self):
        if len(self._cache) <= self.cache_size:
            return
        file_by_age = sorted(self._cache.items(), key=lambda item: item[1].stat().st_mtime)

        for key, path in file_by_age:
            try:
                path.unlink()
                del self._cache[key]
            except OSError as e:
                logger.warning(f"Failed to remove cached file {path}: {e}")


    @staticmethod
    def hash_markdown(tex: str, hash_length: int = 8) -> str:
        """ Gets has value of tex and returns truncated has
        TODO: Figure out the probablity of colllision.

        -- Params --
        hash_length: has will be truncated to satisfy len(hash_truncated) = hash_length
        tex: string containing latex
        """
        hash = hashlib.sha256(tex.encode('utf-8')).hexdigest()
        trucated_hash = hash[:hash_length]
        return trucated_hash

    # TODO
    def list_cache_by_oldest(self) -> OrderedDict[str, Path]:
        """ List cached files by oldest edit ignoring cached files for default messages """
        cache_paths = {hash: Path(filepath) for hash, filepath in self._cache.items() if hash + ".pdf" not in self._ignore_hashes}
        cache_paths_sorted = OrderedDict(sorted(cache_paths.items(), key=lambda item_pair: item_pair[1].stat().st_mtime, reverse=True))
        return cache_paths_sorted

    def keys(self):
        """Return cache keys."""
        return self._cache.keys()

    def values(self):
        """Return cache values."""
        return self._cache.values()

    def items(self):
        """Return cache items."""
        return self._cache.items()

    def get(self, markdown: str, default=None):
        """Get cache value with default."""
        string = "empty" if not markdown else self.hash_markdown(markdown)
        return self._cache.get(string, default)

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()

    def update(self, other: dict[str, Path]) -> None:
        """Update cache with another dictionary."""
        self._cache.update(other)

    def _load_cache(self) -> dict[str, Path]:
        cache = dict()
        for file in self.cache_pdf.iterdir():
            if file.is_file():
                cache[file.name] = file
        return cache

    def __eq__(self, other) -> bool:
        if not isinstance(other, FlashcardCache):
            return NotImplemented

        return (self.cache_root == other.cache_root and
                self._cache == other._cache and
                self._section_names == other._section_names)

    def __hash__(self):
        return hash((self.cache_root, tuple((sorted(self._cache.items()))) if self._cache else ()))

    def __getitem__(self, key: str) -> Path:
        """Get cached file path by filename."""
        try:
            return self._cache[key]
        except KeyError:
            raise KeyError(f"No cached file found for key: {key}")

    def __delitem__(self, key: str) -> None:
        """Remove a cache entry."""
        try:
            filepath = self._cache[key]
            del self._cache[key]
            filepath.unlink()
        except KeyError:
            raise KeyError(f"No cached file found for key: {key}")
        except OSError:
            raise OSError(f"Failed to remove cached file with key: {key}")

    def __len__(self) -> int:
        return len(self._cache)

    def __setitem__(self, key: str, value: Path) -> None:
        self._cache[key] = value

        if len(self._cache) > self.cache_size * 1.2:
            self.cleanup_cache()


    def __contains__(self, key: str) -> bool:
        return key in self._cache

    def __bool__(self) -> bool:
        return bool(self._cache)

    def __lt__(self, other) -> bool:
        if not isinstance(other, FlashcardCache):
            return NotImplemented
        return len(self._cache) < len(other._cache)

    def __repr__(self) -> str:
        return f"FlashcardCache(cache_dir={self.cache_root!r})"


# Currently packages to be used in compilation are specified in format callable. It might be worth making this more dynamic
# Need to add typst template callable
class FlashcardCompiler:
    def __init__(self, cache: FlashcardCache):
        self.cache = cache

    def compile_card(self, card: Flashcard) -> None:
        """ Attemps to compile flashcard question/answer latex. If compilation fails """
        if card.main_section.title is not None:
            card.main_section.title_pdf = self._compile_tracked_text(card.main_section.title)

        card.main_section.pdf_path = self._compile_tracked_text(card.main_section.content)
        if card.proof_section is not None:
            card.proof_section.pdf_path = self._compile_tracked_text(card.proof_section.content)

    def _compile_tracked_text(self, text: TrackedText) -> Path | None:
        source = text.source
        ext = text.filetype().extension
        if text.filetype() == FileType.LaTeX:
            template_func = latex_template
        else:
            template_func = typst_template
        string = str(text)


        if (file := self.cache.get(string)):
            logger.debug(f"Getting file {text.source} from cache")
            return file # should probabily be Path

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
            new_path = pdf_file_path.rename(self.cache.cache_pdf / f"{self.cache.hash_markdown(string)}.pdf").resolve()
        return new_path


