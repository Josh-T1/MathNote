import re
import logging
from typing import SupportsIndex, TypedDict, Union
from collections.abc import Iterable, Iterator, Callable
from pathlib import Path
from dataclasses import dataclass, field

from ..utils import config, FileType

"""
TODO
1. Get macro names dynamically
"""

logger = logging.getLogger("mathnote")

MACRO_PATH = config["macros"]

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

    def __getitem__(self, __key: SupportsIndex | slice) -> 'TrackedText':
        return TrackedText(self.text.__getitem__(__key), source=self.source)

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

    def replace(self, old: str, new: str):
        return TrackedText(self.text.replace(old, new), source=self.source)

    def encode(self, encoding: str = 'utf-8', errors: str = 'strict') -> bytes:
        return self.text.encode(encoding=encoding, errors=errors)

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

    def startswith(self, prefix: str | tuple[str, ...], *args) -> bool:
        return self.text.startswith(prefix, *args)

    def isalpha(self) -> bool:
        return self.text.isalpha()

# We would prefer to have name as enum (containing all section names), however users may define new sections in config file. Look at ImmutableMeta in mathnotelib.utils
# Using SectionNames/SectionNamesDescriptor is hack, not really sure how to fix this
class Section(TypedDict):
    name: str # TODO make Enum
    content: TrackedText
    header: TrackedText

# TODO: .proof
@dataclass
class Flashcard:
    section_name: str
    question: TrackedText
    answer: TrackedText
    pdf_answer_path: None | str = None
    pdf_question_path: None | str = None
    additional_info: dict[str, TrackedText] = field(default_factory=dict)
    seen: bool = False

    def filetype(self) -> FileType:
        return self.question.filetype()

    def add_info(self, name: str, info: TrackedText) -> None:
        self.additional_info[name] = info

    def __repr__(self) -> str:
        question = "..." if self.question else 'None'
        answer = "..." if self.answer else 'None'
        return f"Flashcard(question={question}, answer={answer}, pdf_answer_path={self.pdf_question_path}, pdf_question_path={self.pdf_answer_path}, file_type={self.filetype()})"

    def __str__(self) -> str:
        return f"Flashcard(question={self.question}, answer={self.answer}, pdf_answer_path={self.pdf_question_path}, pdf_question_path={self.pdf_answer_path})"


#def find_math_mode(tex: str):
#    """ This has erros. For some reason it matches double backslash """
#    inline_match = re.match(r"^\\\(.*?\\\)", tex)
#
#    if inline_match != None:
#        return inline_match
#
#    return re.match(r"^\\[.*?\\]", tex)


# TODO refactor to fix this
def get_hack_macros():
    """tmp fix for removing macros"""
    return {"framedtext": {"num_args": '1', "command": ""}}

# TODO re work this
def load_macros(macros_path: Path, macro_names: list[str]) -> dict[str,dict]:
    r""" Gets all user commands from macro_path
    Macros beign parsed have the form:
        \newcommand{macro name}[nargs(int)]{
            command
            }
    returns: dict of the form {cmd_name: {args: #, tex_cmd: ""}}
    """
    logger.debug(f"Calling load_macros with macros_path={macros_path}, macros_names:{macro_names}")
    macros = dict()
    document = Path(macros_path).read_text().splitlines()
    pattern = r'\\newcommand\{(.*?)\}\[(.*?)\]'
    # Makes assumtion that the only characters in 'line' are part of command with the exception of whitespace
    for line in document:
        match = re.search(pattern, line)

        if not match:
            continue
        name = match.group(1).lstrip("\\")

        if name in macro_names:
            tex_cmd = line.replace(match.group(0), "").strip()[1:-1] # remove enclosing curly braces
            macros[name] = {"num_args": match.group(2), "command": tex_cmd}
    logger.debug(f"load_macros returning {macros}")
    return macros
