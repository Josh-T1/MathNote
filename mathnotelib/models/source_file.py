from dataclasses import dataclass
from pathlib import Path
import re
from typing import Callable, Iterable, Iterator, SupportsIndex, Union
from .._enums import FileType

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



# There is an issue with this. In typst optional args can be sarrounded by '()' or '[]' (inline vs block), we will assume users always use '[]'
@dataclass(frozen=True)
class LanguageChars:
    cmd_prefix: str
    comment: str
    arg_open_delim: str
    arg_close_delim: str
    opt_arg_open_delim: str
    opt_arg_close_delim: str
    newline: str


#TODO: should I really have a fallback for FileType.Unsupported?
# rename opt_arg
langauage_char_registry: dict[FileType, LanguageChars] = {
        FileType.LaTeX: LanguageChars(
            cmd_prefix="\\", comment="%", arg_open_delim="{", arg_close_delim="}", opt_arg_open_delim="{", opt_arg_close_delim="}", newline="\n"
            ),
        FileType.Typst: LanguageChars(
            cmd_prefix="#", comment="//", arg_open_delim="(", arg_close_delim=")", opt_arg_open_delim="[", opt_arg_close_delim="]", newline="\n"
            ),
        FileType.Unsupported: LanguageChars(
            cmd_prefix="", comment="#", arg_open_delim="", arg_close_delim="", opt_arg_open_delim="", opt_arg_close_delim="", newline="\n"
            )
        }

class TrackedText:
    def __init__(self, text: str, source: Path | None = None):
        self.text = text
        self.source = source

    def join(self, iterable: Iterable["TrackedText"]) -> "TrackedText":
        if not iterable:
            return TrackedText("")
        joined_text = self.text.join([str(tracked_text) for tracked_text in iterable])
        return TrackedText(joined_text, source = self.source)

    def __getattr__(self, name: str):
        attr = getattr(self.text, name)
        if callable(attr):
            def wrapper(*args, **kwargs):
                result = attr(*args, **kwargs)
                if isinstance(result, str):
                    return TrackedText(result, source=self.source)
                return result
            return wrapper
        return attr

    def filetype(self) -> FileType:
        suffix_map = {".typ": FileType.Typst, ".tex": FileType.LaTeX}
        if self.source is None:
            return FileType.Unsupported
        return suffix_map.get(self.source.suffix, FileType.Unsupported)

    def apply_func(self, func: Callable[[str], str]) -> "TrackedText":
        new_text = func(self.text)
        return TrackedText(new_text)

    def sub(self, pattern: str, repl: str) -> "TrackedText":
        new_text = re.sub(pattern, repl, self.text)
        return TrackedText(new_text, source=self.source)

    def encode(self, encoding: str = 'utf-8', errors: str = 'strict') -> bytes:
        return self.text.encode(encoding=encoding, errors=errors)

    def __getitem__(self, __key: SupportsIndex | slice) -> 'TrackedText':
        return TrackedText(self.text.__getitem__(__key), source=self.source)

    def __bool__(self) -> bool:
        return len(self.text) != 0

    def __add__(self, other: 'TrackedText') -> "TrackedText":
        """
        Other must be of type TrackedText and be of the same file type
        Left add has priority except for the special case where the string on the left has None as source.

        Example:

        T1 = TrackedText(...)
        T2 = TrackedText(...)
        result = T1 + T2

        result.source equals T1.source
        """

        if not isinstance(other, TrackedText):
            raise TypeError(f"Other must be type str not type {type(other)}")
        elif other.source is None or self.source is None:
            return TrackedText(self.text + other.text, source=self.source)
        elif other.source.suffix != self.source.suffix:
            raise TypeError(f"Incompatible source file types, expected filetype {self.source.suffix}, got {other.source.suffix}")
        return TrackedText(self.text + other.text, source=self.source)

    def split(self, sep: str | None = None, maxsep: SupportsIndex = -1) -> list['TrackedText']:
        return [TrackedText(e, source=self.source) for e in self.text.split(sep, maxsep)]

    def __str__(self) -> str:
        return self.text

    def __iter__(self) -> Iterator["TrackedText"]:
        return (TrackedText(c, source=self.source) for c in self.text)

    def __len__(self) -> int:
        return len(self.text)

    def __repr__(self) -> str:
        return (f"TrackedText({self.text}, self.source={self.source})")

    def __contains__(self, item: Union["TrackedText", str]) -> bool:
        if isinstance(item, TrackedText):
            return item.text in self.text
        return item in self.text
