from pathlib import Path
from dataclasses import dataclass
import shutil
import subprocess
import logging
import hashlib
import tempfile
from typing import OrderedDict

from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrinter

from ..models import SourceFile, StandaloneSourceFile, FlashcardSideName, TrackedText, Flashcard
from ..enums import FileType, OutputFormat


logger = logging.getLogger(__name__)

Stderr = str
Stdout = str
CompilationResult = tuple[int, Stderr, Stdout]

# TODO make package dynamic
def latex_template(tex: str, prefix: str | None = None) -> str:
    if prefix is not None:
        tex = fr"\emph{{{prefix}}}: {tex}"
    """ flashcard contents are compiled with the following template """
    return fr"""
\documentclass[preview, border=0.1in]{{standalone}}
\usepackage{{amsmath,amsfonts,amsthm,amssymb,mathtools}}
\usepackage{{mathrsfs}}

\begin{{document}}
{tex}
\end{{document}}"""

# todo make package dynamic
def typst_template(typ: str, prefix: str | None = None, packages: list[dict[str, list[str]]] | None = None) -> str:
    if prefix is not None:
        typ = f'#emph("{prefix}"): {typ}'
    return fr"""
#set page(
        width: 14cm,
        height: auto,
        margin: 15pt
        )
#set text(11pt)
#import "@local/notes:1.0.0": *

{typ}
"""

@dataclass
class CompileOptions:
    filepath: Path
    output_format: OutputFormat
    multi_page: bool = True
    root: Path | None=None
    _output_file_stem: str | None=None
    _output_dir: Path | None=None
    _cwd: Path | None=None

    def set_output_file_stem(self, stem: str):
        # check for "."
        self._output_file_stem = stem

    def set_output_dir(self, dir: Path):
        # ensure valid dir?
        self._output_dir = dir

    def set_cwd(self, cwd: Path):
        self._cwd = cwd

    def resolved_output_path(self) -> Path:
        return self.resolved_output_dir() / f"{self.resolved_output_file_stem()}{self.output_format.extension}"

    def resolved_output_file_stem(self):
        if self._output_file_stem is not None:
            return self._output_file_stem
        return self.filepath.stem

    def resolved_cwd(self):
        if self._cwd is not None:
            return self._cwd
        return self.filepath.parent

    def resolved_output_dir(self):
        if self._output_dir is not None:
            return self._output_dir
        return self.filepath.parent


def interpret_latexmk_exit_code(result: subprocess.CompletedProcess[bytes]) -> str:
    if result.returncode == 0:
        return ""
    if result.returncode == 10:
        return "Invalid arguments were passed to LaTeXmk."
    if result.returncode == 11:
        return "A required file was not found."
    if result.returncode == 12:
        return "A LaTeX tool (pdflatex, bibtex, etc.) failed during compilation."
    return f"LaTeXmk failed. See log:\n{result.stderr.strip()}"

def compile_source(source: SourceFile, options: CompileOptions) -> CompilationResult:
    if source.filetype() == FileType.LaTeX:
        res = compile_latex(source.path, options)
    elif source.filetype() == FileType.Typst:
        res = compile_typst(source.path, options)
    else:
        res = (1, f"Unsupported filetype {source.filetype()}", "")
    return res

def compile_typst(filepath: Path, options: CompileOptions) -> CompilationResult:
    cmd = ["typst", "compile", "--format", options.output_format.value]
    if options.root is not None:
        cmd.extend(["--root", str(options.root)])

    cmd.append(str(filepath))
    if options.output_format == OutputFormat.SVG and options.multi_page:
        cmd.append(f"{options.resolved_output_dir() / options.resolved_output_file_stem()}-{{p}}.svg")
    elif options.output_format == OutputFormat.SVG:
        cmd.append(f"{options.resolved_output_dir() / options.resolved_output_file_stem()}.svg")
    else:
        cmd.append(f"{options.resolved_output_dir() / options.resolved_output_file_stem()}.pdf")

    result = subprocess.run(
        cmd,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
        cwd = options.resolved_cwd()
        )
    if result.returncode != 0 or options.output_format == OutputFormat.PDF:
        return (result.returncode, result.stderr.decode("utf-8"), result.stdout.decode("utf-8"))

    return (result.returncode, result.stderr.decode("utf-8", errors="replace"), result.stdout.decode("utf-8", errors="replace"))


def compile_latex_to_pdf(filepath: Path, options: CompileOptions, verbose_err_msg: bool=False) -> CompilationResult:
    pdf_cmd = ["latexmk",
               "-pdf",
               "-silent",
               "-pdflatex=pdflatex -interaction=nonstopmode",
               f"-outdir={options.resolved_output_dir()}",
               f"-jobname={options.resolved_output_file_stem()}",
               str(filepath)
               ]
    result = subprocess.run(
        pdf_cmd,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
        cwd = options.resolved_cwd()
        )
    error_msg = interpret_latexmk_exit_code(result)
    if verbose_err_msg:
        error_msg += f"\nLatexmk cmd stdour: {result.stderr.decode("utf-8", errors="replace")}"
    return (result.returncode, error_msg, result.stdout.decode("utf-8"))



def compile_latex(filepath: Path, options: CompileOptions):
    svg_cmd = ["pdf2svg",
               f"{options.resolved_output_dir() / options.resolved_output_file_stem()}.pdf",
               ]
    if options.multi_page:
        svg_cmd.append(f"{options.resolved_output_dir() / options.resolved_output_file_stem()}-%d.svg")
        svg_cmd.append("all")
    else:
        svg_cmd.append(f"{options.resolved_output_dir() / options.resolved_output_file_stem()}.svg")

    res = compile_latex_to_pdf(filepath, options)

    output_file = options.resolved_output_dir() / f"{options.resolved_output_file_stem()}.pdf"
    if options.output_format == OutputFormat.PDF or not output_file.exists():
        return (1, res[1], res[2])

    result_2 = subprocess.run(
          svg_cmd,
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
          cwd=options.resolved_cwd()
            )
    return (result_2.returncode, result_2.stderr.decode("utf-8", errors="replace"), result_2.stdout.decode("utf-8", errors="replace"))


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



class FlashcardCompiler:
    def __init__(self, cache: FlashcardCache):
        self.cache = cache

    def compile_card(self, card: Flashcard) -> None:
        """ Attemps to compile flashcard question/answer latex. If compilation fails """
        for k, v in card.sides.items():
            hash = self.cache.hash_markdown(str(v.content))
            cached_res = self.cache.get(hash)
            if isinstance(cached_res, Path):
                print("In cache")
                v.pdf_path = cached_res
                continue
            if k == FlashcardSideName.QUESTION:
                prefix = card.section_name.lower().capitalize()
                pdf = self._compile_tracked_text(v.content, prefix=prefix)
            else:
                pdf = self._compile_tracked_text(v.content)
            if pdf is None:
                raise ValueError(f"Failed to compile flashcard content: {v.content}")
            v.pdf_path = pdf

    def _compile_tracked_text(self, text: TrackedText, prefix: str | None = None) -> Path | None:
        source = text.source
        ext = text.filetype().extension
        if text.filetype() == FileType.LaTeX:
            template_func = latex_template
        else:
            template_func = typst_template
        string = str(text)

        with tempfile.TemporaryDirectory() as tmpdir:
            source_file_path = Path(tmpdir) / f"temp{ext}"
            pdf_file_path = Path(tmpdir) / "temp.pdf"
            source_file_path.write_text(template_func(string, prefix=prefix), encoding='utf-8')
            file = SourceFile(source_file_path)
            options = CompileOptions(source_file_path, OutputFormat.PDF)
            return_code = compile_source(file, options)
            if return_code == 1:
                logger.error(f"Compilation error, file contents: {string}\nSource={source}")
                return

            if not pdf_file_path.is_file(): # Error != no pdf produced
                    return None

            new_path = pdf_file_path.rename(self.cache.cache_pdf / f"{self.cache.hash_markdown(string)}.pdf").resolve()
            self.cache[new_path.stem] = new_path
        return new_path


    # TODO: untested
    def text_to_pdf(self, text: str) -> Path:
        doc = QTextDocument()
        doc.setPlainText(text)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        path = self.cache.cache_pdf / f"{self.cache.hash_markdown(text)}-error.pdf"
        printer.setOutputFileName(str(path))
        doc.print(printer)
        return path
