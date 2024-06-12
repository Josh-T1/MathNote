from collections.abc import Callable
from os import stat
from types import FunctionType
from . import utils
from pathlib import Path
from typing import Type, Union, Tuple, Any
import re
import logging
from abc import abstractmethod, ABC
from dataclasses import KW_ONLY, dataclass, field
from collections import namedtuple
import copy

MACRO_PATH = utils.get_config()["macros-path"]
MACRO_NAMES = ["mlim", "norm", "squarebk", "roundbk", "curlybk", "anglebk", "abs", "operator", "rline",
               "uline"]

TEX_PATTERN_TO_MATHJAX = {r"\\begin\{equation\*\}": r"\[",
                        r"\\end\{equation\*\}": r"\]",
                        ">": "&gt;",
                        "<": "&lt;",
                        "&": "&amp;",
                          }
#Metadata = namedtuple("Metadata", ["start_index", "end_index", "text", "path"])
@dataclass
class Metadata:
# should frozen = True?
    start_index: int
    text: str
    path: Path
    change_log: list[str] = field(default_factory=list)

    @property
    def end_index(self):
        """ Inclusive """
        return self.start_index + len(self.text) -1

class TrackedString:
    """
    TrackedString tries to implement 'duck typing' by implementing all behaviour associated with strings with additional features such as storing souce data,
    such as file_path, if applicable.


    --- Limitations:
        1. self.apply_text_modifier method makes strong assumtion that pattern matching callbacks will trigger same action on both Metadata.text
        when Metadata.text is standalone string and Metadata.text when its a substring. This fails when we have pattern = <pattern_start>any<pattern_end> and
        string = '<pattern_start>Metadata.text<pattern_end>',
        string = '<pattern_start><Metadata.text(when Metadata.text is pattern_end/pattern_start)',
        ect (way to many cases)

        2. Name needs to be changed or class needs to change. We implement features specific to this project while calling keeping the general name TrackedString.
        Im not even sure we need this class... Need a way to pass information of string to Flashcard class eventually, this becomes complicated when string is modified.
        Can we really say the source file is ex.text is every line changes? but those changes where made to text from ex.tex


    """
    def __init__(self, metadata: list[Metadata] | None = None):
        self.metadata_list = metadata if metadata is not None else []

    def apply_text_modifier(self, callback: Callable[[str], str]):
        """
        ** Warning ** will not work with all pattern matching callbacks as we assume that calback(metadata1.text) will trigger the same action on metadata1.text as
        callback(''.join([metadata.text for metadata in metadatalist])) on the substring metadata1.text.
        TODO: Implement optional, slower but exauhstive method for catching changes to string.
        """
        adjustment = 0
        for index, meta_obj in enumerate(self.metadata_list):
            old_text = meta_obj.text
            new_text = callback(old_text)
            if old_text != new_text:
                self.metadata_list[index].text = new_text
                self.metadata_list[index].start_index = self.metadata_list[index].start_index + adjustment
                self.metadata_list[index].change_log.append(callback.__name__)
                adjustment += len(old_text) - len(new_text)
        return self

    @property
    def text(self):
        return "".join([metadata.text for metadata in self.metadata_list])

    def __add__(self, other) -> 'TrackedString':
        if not isinstance(other, TrackedString):
            raise TypeError(f"Can only concatinate TrackedString with TrackedString not TrackedString with {type(other)}")
        last_index = self.metadata_list[-1].end_index
        for metadata in other.metadata_list:
            pass
        combined_metadata = self.metadata_list + other.metadata_list
        return TrackedString(combined_metadata)

    def __getitem__(self, key) -> str:
        if not self.metadata_list:
            return ""
        if isinstance(key, slice):
            if key.stop > self.metadata_list[-1].end_index or key.start < 0:
                raise KeyError(f"{slice} is out of bounds")
            return self.text[key]

        elif isinstance(key, int):
            if key > self.metadata_list[-1].end_index:
                raise KeyError(f"{slice} is out of bounds")
            return self.text[key]

        else:
            raise TypeError(f"Invalid key type: {type(key)}")

    def get_slice_metadata(self, key: Union[slice, int] ) -> list[Metadata]:
        """ Returns list of 'sliced' Metadata objects. These Metadata objects are relative to the TrackedString instance.
        Meaning that start_index of the first Metadata object is relative to the TrackedString instance and all Metadata objects contained in self.metadata_list.
        If a Metadata object is partially in bounds of a slice, a 'sliced' Metadata objects is using the sliced data of the original Metadata object.
        All Metadata objects returned are new objects, as opposed to references to the original objects stored in self.metadata_list
        -- Params --
        key: slice object
        """
        data = []
        if isinstance(key, int):
            key = slice(key, key+1)

        if key.start < 0 or key.stop > self.metadata_list[-1].end_index:
            raise KeyError(f"Slice: {key} is out of bounds")

        for metadata in self.metadata_list:
            if metadata.end_index < key.start:
                continue
            if metadata.start_index > key.stop:
                break
            slice_start = max(metadata.start_index, key.start)
            slice_end = min(metadata.end_index, key.stop)
            slice_text = metadata.text[slice_start:slice_end:key.step]
            data.append(Metadata(slice_start, slice_text, metadata.path))
        return data

    def __contains__(self, string: str):
        return string in self.text

    def __len__(self):
        return len(self.text)

    def __ge__(self, other):
        if not isinstance(other, TrackedString):
            raise ValueError("Comparison only available betweeen 'TrackedString' and 'TrackedString'")
        return self.text > other.text

    def __le__(self, other):
        if not isinstance(other, TrackedString):
            raise ValueError("Comparison only available betweeen 'TrackedString' and 'TrackedString'")
        return self.text <= other.text

    def __eq__(self, other) -> bool:
        if not isinstance(other, TrackedString):
            raise ValueError("Comparison only available betweeen 'TrackedString' and 'TrackedString'")
        return self.text == other.text

    def __str__(self) -> str:
        return self.text

    def __getattr__(self, name):
        return getattr(self.text, name)
    def lower(self):
        return self.text.lower()
    def upper(self):
        return self.text.upper()
@dataclass
class Flashcard:
    question: str
    answer: str
    error_message: str = ""
    pdf_answer_path: None | str = None
    pdf_question_path: None | str = None


class EmptyFlashcard(Flashcard):
    def __init__(self) -> None:
        super().__init__(question="", answer="", error_message="No flashcards available to display")
# Macros needs to be re thought.


class Stage(ABC):
    @abstractmethod
    def process(self, data):
        pass

class GetDataStage(Stage):
    def __init__(self, file_paths: list[Path]) -> None:
        super().__init__()
        self.file_paths = file_paths
        self.file_contents = TrackedString()

    def _load_file_contents(self):
        for file_path in self.file_paths:
            file_contents = file_path.read_text(encoding='utf-8')
            tracked_file_contents = TrackedString([Metadata(0, file_contents, file_path)])
            self.file_contents += tracked_file_contents

    def process(self, data=None):
        self._load_file_contents()
        return self.file_contents

class CleanStage(Stage):
    def __init__(self, macros: dict) -> None:
        super().__init__()
        self.macros = macros

    def process(self, data: TrackedString) -> TrackedString:
        data.apply_text_modifier(self.remove_comments)
        data.apply_text_modifier(self.remove_macros)
        return data

    def replace_macros(self):
        pass

    def remove_comments(self, tex: str):
        pattern = r'% .*?\n'
        return re.sub(pattern, '', tex)

    def _find_cmd(self, tex: str, macros: list[str]) -> Union[str, None]:
        """ It is assumed tex string starts with backslash character """
        for pattern in macros:
            if tex.startswith(pattern):
                return pattern
        return None

    @staticmethod
    def _find_arg(tex: str) -> Union[str, None]:
        """ It is assume the tex string passed starts with curly bracket """
        paren_stack = []

        if tex[0] != "{": # } <- this comment is to keep vim lsp happy
            raise ValueError(f"String passed does not begin with curly opeining brace: {tex[:20]}")

        for index, char in enumerate(tex):
            if char == "{":
                paren_stack.append(char)
            elif char == "}":
                paren_stack.pop()
            if not paren_stack:
                return tex[1:index]
        return None



    def remove_macros(self, tex: str) -> str:
        """ Replaces all user defined macros with 'pure tex' in the sence that it would compile without a specific macros.tex/preamble.tex
        ** Limited to replacing macros of the form: \\macro_name{title}{tex}. This can not handle more complex macros
        :param tex: latex code as string
        :param macros: dictionary with key values of the form; macro_name: macro_dict_info. ie {defin: {command_in_tex: tex, ....},...}
        """
        new_tex = ""
        counter = 0

        while counter < len(tex): # check this is what i want

            if tex[counter] != '\\':
                new_tex += tex[counter]
                counter += 1
                continue

            cmd = self._find_cmd(tex[counter+1:], list(self.macros.keys()))

            if cmd == None:
                new_tex += tex[counter]
                counter += 1
                continue

            end_cmd_index = counter + len(cmd)  # -1 to accound for backslash character being in command, we want all end_*_index variables to be inclusive
            arg = self._find_arg(tex[end_cmd_index +1:])

            if arg == None:
                logging.warn("Something went wrong while calling clean_self.tex")
                break

            cleaned_arg = self.remove_macros(arg)
            new_cmd = self.macros[cmd]["command"].replace("#1", f" {cleaned_arg} ")

            num_brackets_ignored = 2
            new_tex += f" {new_cmd} " # Aviod issues of the from \norm{f_n}g(x) -> \lVert f_n \rVertg(x), where \rVertg(x) raises an error when compiled
            counter = len(arg) + end_cmd_index + num_brackets_ignored +1 # This sets counter equal to last character in command, +1 to move to character after command
        return new_tex

class FilterStage(Stage):
    """ THis is where I can filter doc by section """
    def __init__(self, section_names: list[str]) -> None:
        super().__init__()
        self.section_names = section_names

    def process(self, tex):
        return tex

class FilterBySectionStage(FilterStage):
    def __init__(self, section_names: list[str]) -> None:
        super().__init__(section_names)

    def _find_section_titles(self, line: str): # Figure out how to have match type
        """ Checks to see if macro box is present in line
        returns: string or None"""

        for section_name in self.section_names: #type: ignore
            pattern = rf'^\\({section_name}){{(.*?)}}' # }}
            match = re.search(pattern, line)
            if match:
                return match
        return None

    @staticmethod
    def index_of_line_end(tex: str):
        """
        :param tex: latex code as string
        :returns int: index of line end, None if no newline character, could occur on last line in file
        """
        for index, char in enumerate(tex):
            if char == "\n":
                return index +1
        return None

    @staticmethod
    def _find_arg(tex: str) -> Union[str, None]:
        """ It is assume the tex string passed starts with curly bracket """
        paren_stack = []

        if tex[0] != "{": # } <- this comment is to keep vim lsp happy
            raise ValueError(f"String passed does not begin with curly opeining brace: {tex}")

        for index, char in enumerate(tex):
            if char == "{":
                paren_stack.append(char)
            elif char == "}":
                paren_stack.pop()
            if not paren_stack:
                return tex[1:index]
        return None

    def process(self, tex):
        pass

class TransformStage(Stage):
    pass

class FilterBySectionAndMakeFlashcardsStage(FilterBySectionStage):
    def __init__(self, section_names: list[str]) -> None:
        super().__init__(section_names)


    def process(self, data):
        """
        :param data: data as string
        :param section_names: gets all data from sections contained in section_names
        :returns list: [(name, section_contents)....] """
        flashcards = []
        counter = 0
        while counter < len(data): # check this is what i want

            if data[counter] == "%": # Do this everywhere
                comment_len = self.index_of_line_end(data[counter+1:])

                if comment_len == None:
                    raise Exception("This is probably not good... ")

                counter += comment_len
                continue

            if data[counter] != '\\':
                counter += 1
                continue

            match = self._find_section_titles(data[counter:])

            if match == None:
                counter += 1
                continue

            end_cmd_index = counter + len(match.group(0))
            section_contents = self._find_arg(data[end_cmd_index:])

            if section_contents == None:
                break
            flashcards.append(
                    Flashcard(match.group(2),section_contents)
                    )
            counter = len(section_contents) + end_cmd_index + 1  # This sets counter equal to last character in command, +1 to move to character after command
        return flashcards


class FlashcardsPipeline:
    def __init__(self, stages: list[Stage]):
        self.stages = stages

    def run(self) -> Any:
        data = []
        for stage in self.stages:
            data = stage.process(data)
        return data

def find_math_mode(tex: str):
    """ This has erros. For some reason it matches double backslash """
    inline_match = re.match(r"^\\\(.*?\\\)", tex)

    if inline_match != None:
        return inline_match

    return re.match(r"^\\[.*?\\]", tex)


def tex_to_mathjax(tex: str):
    for pattern, replacement in TEX_PATTERN_TO_MATHJAX.items():
        tex = re.sub(pattern, replacement, tex)
    return tex


def mathjax_to_html(tex: str):
    html = ""
    counter = 0
    while counter < len(tex): # check this is what i want
        if tex[counter] != '\\':
            html += tex[counter]
            counter += 1
            continue

        match = find_math_mode(tex[counter:])

        if match == None or match.group(0) == r'\\':
            html += tex[counter]
            counter += 1
            continue

        math_mode = "inline" if match.group(0)[1] == "(" else "display" # )
        math_block = f'<span class="math {math_mode}">{match.group(0)}</span>'
        html += math_block

        counter = counter + len(match.group(0)) + 1 # This sets counter equal to last character in command, +1 to move to character after command

    return html

def load_macros(macros_path: Path, macro_names: list[str]) -> dict[str,dict]:
    r""" Gets all user commands from self.macros_path
    Macros beign parsed have the form:
        \macro_name{name(optional)}{
            something(optional)
            }
    returns: dict of the form {cmd_name: {args: #, tex_cmd: ""}}
    """
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
    return macros
