from dataclasses import dataclass
from pathlib import Path
import re

from ..utils import FileType

"""
TODO: we get errors from latexmk, but output is still produced. Look into different error code meanings.
Currently we can just check for output file to validate compilation
"""

@dataclass
class SourceFile:
    path: Path

    def file_type(self) -> FileType:
        map = {".tex": FileType.LaTeX, ".typ": FileType.Typst}
        return map.get(self.path.suffix, FileType.Unsupported)

    @property
    def name(self) -> str:
        return self.path.stem


@dataclass
class StandaloneSourceFile(SourceFile):
    def pdf_path(self) -> Path | None:
        pdf_path = self.path.parent / self.path.with_suffix(".pdf").name
        if pdf_path.exists():
            return pdf_path
        return None

@dataclass
class ProjectSourceFile(SourceFile):
    main_file: Path

class Assignment(StandaloneSourceFile):
    def number(self) -> int:
        pattern = r"-A(\d+)"
        matches = re.findall(pattern, self.path.name)
        if len(matches) == 0:
            return 0
        else:
            return int(matches[-1])

class Lecture(ProjectSourceFile):
    def __post_init__(self):
        assert self.file_type() != FileType.Unsupported

    def number(self) -> int:
        """" returns: lecture number """
        num = int(self.path.stem.replace('lec_', '').lstrip("0"))
        return num

    @property
    def name(self) -> str:
        """ lecture file name. e.g lec_01.tex(typ) """
        return self.path.name

    def last_edit(self) -> float:
        """ Returns most recent edit in seconds """
        return self.path.stat().st_mtime



#class CompilableCourseFiles(TypedDict):
#    main: SourceFile | None
#    assignments: list[Assignment]
#    lectures: list[Lecture]


#    def open(self):
#        """
#        Opens note as pdf
#        """
#        pdf_path = self.path.with_suffix(".pdf")
#        if not pdf_path.is_file():
#            print(f"{pdf_path} not found, attempting to compile note {self.path.stem}")
#            # TODO
#            self.compile()
#        # remove this-use return code
#        if not pdf_path.is_file():
#            print("Failed to compile")
#            return
#
#        open = open_cmd()
#        subprocess.run([open, pdf_path], stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL, cwd=self.path.parent)




