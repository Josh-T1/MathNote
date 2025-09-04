from pathlib import Path
from dataclasses import dataclass
import shutil
import subprocess

from ..models import SourceFile, StandaloneSourceFile
from .filesystem import open_cmd
from .._enums import FileType, LatexmkReturnCode, OutputFormat


@dataclass
class CompileOptions:
    filepath: Path
    output_format: OutputFormat
    multi_page: bool = True
    _output_file_stem: str | None=None
    _output_dir: Path | None=None
    _cwd: Path | None=None

    def set_output_file_stem(self, stem: str):
        self._output_file_stem = stem

    def set_output_dir(self, dir: Path):
        self._output_dir = dir

    def set_cwd(self, cwd: Path):
        self._cwd = cwd

    def resolved_output_path(self) -> Path:
        suffix = ".svg" if OutputFormat.SVG else ".pdf"
        return self.resolved_output_dir() / f"{self.resolved_output_file_stem()}{suffix}"

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

def open_pdf(source: StandaloneSourceFile, lazy: bool=True) -> int:
    pdf_path = source.pdf_path()
    if pdf_path is None or lazy is False:
        options = CompileOptions(source.path, output_format=OutputFormat.PDF)
        compile_source(source, options)

        pdf_path = source.pdf_path()
        if pdf_path is None:
            return False

    open = open_cmd()
    result = subprocess.run([open, pdf_path], stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    return result.returncode


Stderr = str
Stdout = str
CompilationResult = tuple[int, Stderr, Stdout]

def compile_source(source: SourceFile, options: CompileOptions) -> CompilationResult:
    if source.filetype() == FileType.LaTeX:
        res = compile_latex(source.path, options)
    elif source.filetype() == FileType.Typst:
        res = compile_typst(source.path, options)
    else:
        res = (1, f"Unsupported filetype {source.filetype()}", "")
    return res

def compile_typst(filepath: Path, options: CompileOptions) -> CompilationResult:
    cmd = ["typst", "compile", "--format", options.output_format.value, str(filepath)]
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
        cwd = filepath.parent # Hack, cant figure out how to specify out dir in tpyst compile
        )
    if result.returncode != 0 or options.output_format == OutputFormat.PDF:
        return (result.returncode, result.stderr.decode("utf-8"), result.stdout.decode("utf-8"))

    # Move files as a workaround for lack of output directory flag
    files = filepath.glob(f"{options.resolved_output_file_stem()}*.svg")
    for f in files:
        try:
            shutil.move(f, options.resolved_output_dir() / f"{options.resolved_output_file_stem()}.svg")
        except Exception as e:
            return (1, "Failed to move compiled files to output directory (see compiler.py, this is a hack for lack of typst --outdir)", "")
    return (result.returncode, result.stderr.decode("utf-8", errors="replace"), result.stdout.decode("utf-8", errors="replace"))

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


def latex_template(tex: str) -> str:
    """ Flashcard contents are compiled with the following template """
    return fr"""
\documentclass[preview, border=0.1in]{{standalone}}
\usepackage{{amsmath,amsfonts,amsthm,amssymb,mathtools}}
\usepackage{{mathrsfs}}
\begin{{document}}
{tex}
\end{{document}}"""

# TODO
def typst_template(typ: str) -> str:
    return fr"""
#set page(
        width: auto,
        height: auto,
        margin: 5pt
        )
{typ}
"""

