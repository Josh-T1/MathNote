from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import subprocess
import shutil

from .source_file import OutputFormat, TypsetFile
from ..utils import rendered_sorted_key

@dataclass
class TypsetCompileOptions:
    file: TypsetFile
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
        return self.file.path.stem

    def resolved_cwd(self):
        if self._cwd is not None:
            return self._cwd
        return self.file.path.parent

    def resolved_output_dir(self):
        if self._output_dir is not None:
            return self._output_dir
        return self.file.path.parent

def compile_typst(file: TypsetFile, options: TypsetCompileOptions):
    cmd = ["typst", "compile", "--format", options.output_format.value, str(file.path)]
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
        cwd = file.path.parent # Hack, cant figure out how to specify out dir in tpyst compile
        )
    if result.returncode != 0 or options.output_format == OutputFormat.PDF:
        return result.returncode

    # Move files as a workaround for lack of output directory flag
    files = sorted(file.path.glob(f"{options.resolved_output_file_stem()}*.svg"), key=rendered_sorted_key)
    #partial_out_name = output_filename.split(".")[0]
    for f in files:
        try:
            shutil.move(f, options.resolved_output_dir() / f"{options.resolved_output_file_stem()}.svg")
        except Exception as e:
            return 1
    return result.returncode



def compile_latex_to_pdf(file: TypsetFile, options: TypsetCompileOptions):
    pdf_cmd = ["pdflatex",
               "-interaction=nonstopmode",
               f"-output-dir={options.resolved_output_dir()}",
               f"-jobname={options.resolved_output_file_stem()}",
               str(file.path)
               ]
    result = subprocess.run(
        pdf_cmd,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
        cwd = options.resolved_cwd()
        )

    return result.returncode

def compile_latex(file: TypsetFile, options: TypsetCompileOptions):
    svg_cmd = ["pdf2svg",
               f"{options.resolved_output_dir() / options.resolved_output_file_stem()}.pdf",
               ]
    if options.multi_page:
        svg_cmd.append(f"{options.resolved_output_dir() / options.resolved_output_file_stem()}-%d.svg")
        svg_cmd.append("all")
    else:
        svg_cmd.append(f"{options.resolved_output_dir() / options.resolved_output_file_stem()}.svg")

    return_code = compile_latex_to_pdf(file, options)

    if options.output_format == OutputFormat.PDF or return_code !=0:
        return return_code
    result_2 = subprocess.run(
          svg_cmd,
          stdout=subprocess.DEVNULL,
          stderr=subprocess.DEVNULL,
          cwd=options.resolved_cwd()
            )
    return result_2.returncode
