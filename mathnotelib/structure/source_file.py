from dataclasses import dataclass
from pathlib import Path
from enum import Enum
from typing import Optional
import subprocess
import shutil
import platform

from ..utils import FileType

"""
TODO: we get errors from latexmk, but output is still produced. Look into different error code meanings.
Currently we can just check for output file to validate compilation
"""

def open_cmd() -> str:
    """
    Returns the open command for the respective operating system
    """
    system_name = platform.system().lower()
    if system_name == "darwin":
        cmd = "open"
    elif system_name == "linux":
        cmd = "xdg-open"
    else:
        cmd = "start"
    return cmd

class OutputFormat(Enum):
    PDF = "pdf"
    SVG = "svg"

@dataclass
class CompileOptions:
    filepath: Path
    output_format: OutputFormat
    multi_page: bool = True
    _output_file_stem: Optional[str] = None
    _output_dir: Optional[Path] = None
    _cwd: Optional[Path] = None

    def set_output_file_stem(self, stem: str):
        self._output_file_stem = stem

    def set_output_dir(self, dir: Path):
        self._output_dir = dir

    def set_cwd(self, cwd: Path):
        self._cwd = cwd

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

@dataclass
class SourceFile:
    path: Path

    def file_type(self) -> FileType:
        map = {".tex": FileType.LaTeX, ".typ": FileType.Typst}
        return map.get(self.path.suffix, FileType.Unsupported)

    @property
    def name(self) -> str:
        return self.path.stem

    # TODO: improve error msg, return code 1 vs 0 is not ideal
    def compile(self, options: CompileOptions) -> int:
        if self.file_type() == FileType.LaTeX:
            code = compile_latex(self.path, options)
        elif self.file_type() == FileType.Typst:
            code = compile_typst(self.path, options)
        else:
            code = 1
        return code

    def pdf_path(self) -> Path | None:
        pdf_path = self.path.parent / self.path.with_suffix(".pdf").name
        if pdf_path.exists():
            return pdf_path
        return None

    def open_pdf(self, lazy: bool=True) -> int:
        pdf_path = self.pdf_path()
        if pdf_path is None or lazy is False:
            options = CompileOptions(self.path, output_format=OutputFormat.PDF)
            self.compile(options)

            pdf_path = self.pdf_path()
            if pdf_path is None:
                return False

        open = open_cmd()
        result = subprocess.run([open, pdf_path], stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        return result.returncode


def compile_typst(filepath: Path, options: CompileOptions):
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
        return result.returncode

    # Move files as a workaround for lack of output directory flag
    files = filepath.glob(f"{options.resolved_output_file_stem()}*.svg")
    #partial_out_name = output_filename.split(".")[0]
    for f in files:
        try:
            shutil.move(f, options.resolved_output_dir() / f"{options.resolved_output_file_stem()}.svg")
        except Exception as e:
            return 1
    return result.returncode



def compile_latex_to_pdf(filepath: Path, options: CompileOptions):
    pdf_cmd = ["latexmk",
               "-pdf",
               "-silent",
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
    return result.returncode

def compile_latex(filepath: Path, options: CompileOptions):
    svg_cmd = ["pdf2svg",
               f"{options.resolved_output_dir() / options.resolved_output_file_stem()}.pdf",
               ]
    if options.multi_page:
        svg_cmd.append(f"{options.resolved_output_dir() / options.resolved_output_file_stem()}-%d.svg")
        svg_cmd.append("all")
    else:
        svg_cmd.append(f"{options.resolved_output_dir() / options.resolved_output_file_stem()}.svg")

    return_code = compile_latex_to_pdf(filepath, options)

    output_file = options.resolved_output_dir() / f"{options.resolved_output_file_stem()}.pdf"
    if options.output_format == OutputFormat.PDF or not output_file.exists():
        return return_code

    result_2 = subprocess.run(
          svg_cmd,
          stdout=subprocess.DEVNULL,
          stderr=subprocess.DEVNULL,
          cwd=options.resolved_cwd()
            )
    return result_2.returncode
