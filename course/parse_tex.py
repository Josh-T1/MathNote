from . import utils
import time
from functools import partial
from pathlib import Path
from typing import Iterable, Required, Union, Generator, List, Callable
import re
import logging
from abc import abstractmethod, ABC
from dataclasses import dataclass
import copy
from ..global_utils import get_config

logger = logging.getLogger(__name__)

"""
This primary purpose is of parse_tex.py is to provide a customizable pipeline that takes in file paths (.tex files) and returns 'cleaned' tex. This cleaned latex code can then
be utilized to build Flashcards objects, or converted to other formats such as mathjax. Currenlty this module only provides a pipeline builder and pipeline stages relavent for
creating flashcard. Any other functionality, such as converting impure latex code (latex code with user defined shortcuts) to mathjax would require the creation of new pipleline stages and builder.


--- Limitations
1. TexDataGenerator is limited in how the 'chunks' are generated. Fairly easy fix... however not necessary when reading small files.
2. Speed, running the FlashcardsPipeline takes forever. Very possible using TrackString results in poor performace
3. TrackString needs to be re wrote, it does not make sence to track every change and its current design is overkill for tracking only the root source
4. Mostly untested code

--- Notes/TODO
The lsp warning Cannot access memeber '._source_history' from TrackString can be ignored. The TrackString class is not inizialized with that property as it subclasses str which is
immutable. However when __new__ is called the property is set. If there is a way to do this 'properly' that would be great
"""

MACRO_PATH = get_config()["macros-path"]


# TODO:  load these in a more dynmaic way
MACRO_NAMES = ["mlim", "norm", "squarebk", "roundbk", "curlybk", "anglebk", "abs", "operator", "rline",
               "uline", "mylist"]

# this is unfinished as I realized I do not need to convert tex to mathjax. Could be usefull eventually
TEX_PATTERN_TO_MATHJAX = {r"\\begin\{equation\*\}": r"\[",
                        r"\\end\{equation\*\}": r"\]",
                        ">": "&gt;",
                        "<": "&lt;",
                        "&": "&amp;",
                          }

@dataclass(frozen=True)
class PathSourceRecord:
    root: str
    line_number: int | None = None


class TrackedString(str):
    """
    TrackedString tries to use 'duck typing' by implementing all behaviour associated with strings, with additional features such
    as storing souce data. This data could look like a file_path or the name of a callable that 'created' the string.


    --- Limitations:
        1. We give priority to left TrackedString. If string = TrackedString1(...) + TrackedString2(...) string.source_history will only contain
        the history of TrackedString1(...). This asserts there will always be exactly one 'root' source at the expense of tracking 'all' sources
        2. Speed most likley
    """

    def __new__(cls, string,  source_history: PathSourceRecord | None = None):
        instance = super().__new__(cls, string)
        instance.source_history = source_history #type: ignore
        return instance

    def join(self, iterable):
        if not iterable:
            return TrackedString("")

        joined_tex = self.__str__().join([str(tracked_string) for tracked_string in iterable])
        source_history = iterable[0].source_history
        return TrackedString(joined_tex, source_history=source_history)


    def __getitem__(self, __key) -> 'TrackedString':
        return TrackedString(super().__getitem__(__key), source_history=self.source_history)

    def modify_text(self, func: Callable[[str], str]):
        """ Method for using Trackedstring as argument for function: str -> str and using output to create new Trackedstring
        -- Params --
        func: function with str type param and str return type. functools.partial is helpfull here"""
        new_text = func(self.__str__())
        return TrackedString(new_text, source_history=self.source_history)

    def sub(self, pattern: str, repl: str) -> "TrackedString":
        new_text = re.sub(pattern, repl, self.__str__())
        return TrackedString(new_text, self.source_history)

    def __add__(self, other):
        """ Left add has priority. If result = TrackedString1(...) + TrackedString2(...), result.source_history.parent = TrackedString1(...) """
        if not isinstance(other, str):
            raise TypeError(f"Other must be type str not type {type(other)}")
        other_text = other if not isinstance(other, TrackedString) else other.__str__()
        return TrackedString(super().__str__() + other_text,
                             source_history=self.source_history)

    def __ge__(self, other):
        if not isinstance(other, str):
            raise TypeError(f"'>=' not supported between instances of 'TrackedString' and {type(other)}")
        return super().__ge__(other)

    def __le__(self, other: str):
        if not isinstance(other, str):
            raise TypeError(f"'<=' not supported between instances of 'TrackedString' and {type(other)}")
        return super().__le__(other)

    def __lt__(self, other: str):
        if not isinstance(other, str):
            raise TypeError(f"'<' not supported between instances of 'TrackedString' and {type(other)}")
        return super().__lt__(other)

    def __gt__(self, other: str):
        if not isinstance(other, str):
            raise TypeError(f"'>' not supported between instances of 'TrackedString' and {type(other)}")
        return super().__ge__(other)

    def __eq__(self, other) -> bool:
        if not isinstance(other, str):
            raise TypeError(f"'==' not supported between instances of 'TrackedString' and {type(other)}")
        return super().__eq__(other)

    def __repr__(self):
        return (f"TrackedString({super().__repr__()}, self._source_history=SourceHistory(...))")


@dataclass
class Flashcard:
    question: TrackedString
    answer: TrackedString
#    error_message: str = ""
    pdf_answer_path: None | str = None
    pdf_question_path: None | str = None
    seen: bool = False

    def __str__(self):
        # TODO re write this
        question = "Yes" if self.question else 'No'
        answer = "Yes" if self.answer else 'No'
        pdf_question_path = "Yes" if self.pdf_question_path else 'No'
        pdf_answer_path = "Yes" if self.pdf_answer_path else 'No'
        return f"Flashcard(question={question}, answer={answer}, pdf_answer_path={pdf_answer_path}, pdf_question_path={pdf_question_path})" #Blindly using repr() as suggested by chat gpt to escape characters.. that has never created issues for me


class Stage(ABC):
    @abstractmethod
    def process(self, data: TrackedString) -> TrackedString:
        pass

class BuildFlashcardStage(ABC):
    @abstractmethod
    def build(self, data: TrackedString) -> list[Flashcard]:
        pass

class TexDataGenerator:
    """ Generates data in chunks. Each chunk corresponds to the contents of a file... Works well with 'lecture' tex files (small files), could use a re design
    to inlcude a chunk_size param if we are reading from any tex file
    """
    def __init__(self, file_paths: list[Path]) -> None:
        super().__init__()
        self.file_paths = file_paths

    def __iter__(self):
        for file_path in self.file_paths:
            try:
                file_contents = file_path.read_text(encoding='utf-8')
            except Exception as e:
                logger.error(f"Failed to read file {file_path}\n{e}")
                yield None
                continue

            source_history = PathSourceRecord(str(file_path))
            yield TrackedString(file_contents, source_history=source_history) # Borderline retarted to return list with one element


class CleanStage(Stage):
    def __init__(self, macros: dict) -> None:
        super().__init__()
        self.macros = macros

    def process(self, data: TrackedString) -> TrackedString:
        logger.info(f"Starting {self.process}")
        tracked_string = self.remove_comments(data)
        tracked_string = self.remove_macros(tracked_string)
        logger.debug(f"Finished {self.process}")
        return tracked_string


    def remove_comments(self, tex: TrackedString) -> TrackedString:
        pattern = r'% .*?\n'
        return tex.sub(pattern, '')

    def _find_cmd(self, tex: str, macros: list[str]) -> Union[str, None]:
        """ It is assumed tex string starts with backslash character """
        for pattern in macros:
            if tex.startswith(pattern) and not tex[len(pattern)].isalpha(): # Not sure this covers all cases. We make sure line starts with command and next letter is not alphanumeric as that would indicate we got partial match. ie matching operator on operatorname
                return pattern
        return None

    @staticmethod
    def _find_arg(tex: TrackedString) -> Union[TrackedString, None]:
        """ It is assume the tex string passed starts with curly bracket """
        paren_stack = []

        if tex[0] != "{": # } <- this comment is to keep vim lsp happy
            raise ValueError(f"String passed does not begin with curly opening brace: {tex[:50]}, {tex.source_history.root}")

        for index, char in enumerate(tex):
            if char == "{":
                paren_stack.append(char)
            elif char == "}":
                paren_stack.pop()
            if not paren_stack:
                return tex[1:index]
        return None

    def remove_macros(self, tex: TrackedString) -> TrackedString:
        """ Replaces all user defined macros with 'pure tex' in the sence that it would compile without a specific macros.tex/preamble.tex
        ** Limited to replacing macros of the form: \\macro_name{title}{tex}. This can not handle more complex macros
        :param tex: latex code as string
        :param macros: dictionary with key values of the form; macro_name: macro_dict_info. ie {defin: {command_in_tex: tex, ....},...}
        """
        tex_pcs = []
        counter = 0

        while counter < len(tex):

            if tex[counter] != '\\':
                tex_pcs.append(tex[counter])
                counter += 1
                continue

            cmd = self._find_cmd(tex[counter+1:], list(self.macros.keys()))

            if cmd == None:
                tex_pcs.append(tex[counter])
                counter += 1
                continue

            end_cmd_index = counter + len(cmd)  # -1 to accound for backslash character being in command, we want all end_*_index variables to be inclusive
            arg = self._find_arg(tex[end_cmd_index +1:])

            if arg is None:
                logging.warn("Something went wrong while calling clean_self.tex")
                break

            cmd_template = self.macros[cmd]["command"]
            cleaned_arg = self.remove_macros(arg)
            cleaned_arg = self.add_arg_spaces(cmd_template, cleaned_arg)

            new_cmd = cmd_template.replace("#1", cleaned_arg)
            num_brackets_ignored = 2

            if tex[counter-1].isalpha(): # Add space character to prevent joining text, however ensure previous charcater is
                new_cmd = " " + new_cmd
            new_cmd += " "
            tex_pcs.append(TrackedString(new_cmd, source_history=cleaned_arg.source_history))
#            new_tex = TrackedString(str(new_tex) + new_cmd, cleaned_arg.source_history) # Hack solution to ensure TrackedString.source_history.root is correct
            counter = len(arg) + end_cmd_index + num_brackets_ignored +1 #This sets counter equal to last character in command, +1 to move to character after command
        new_tex = TrackedString("").join(tex_pcs)
        return new_tex

    def add_arg_spaces(self, command: str, arg: TrackedString):
        command_split = command.split("#1")
        if command_split[1][0].isalpha():
            arg += " "
        if command_split[0][-1].isalpha():
            arg = arg.modify_text(" ".__add__)
        return arg



class FilterBySectionStage(Stage):
    def __init__(self, section_names: list[str]) -> None:
        super().__init__()
        self.section_names = section_names

    def _find_section_titles(self, line: TrackedString) -> tuple | None:
        """ We assume that the TrackedString starts with \\
        Returns command with \\ character included"""
        for section_name in self.section_names:

            if line[1:].startswith(section_name):

                arg = self._find_arg(line[1+ len(section_name):])
                if not arg:
                    return None
                end_index = len(section_name) + len(arg) + 3 # -2 to account for zero index, +1 for \\, +1 for opening curly brace, + 1 for closing curly brace, +1 since its non inclusive,
                # return wholematch, arg, section_name
                return (line[:end_index], section_name, arg)

        return None


    @staticmethod
    def index_of_line_end(tex: TrackedString) -> int | None:
        """
        :param tex: latex code as string
        :returns int: index of line end, None if no newline character, could occur on last line in file
        """
        for index, char in enumerate(tex):
            if char == "\n":
                return index +1
        return None

    @staticmethod
    def _find_arg(tex: TrackedString) -> Union[TrackedString, None]:
        """ It is assume the tex string passed starts with curly bracket """
        paren_stack = []

        if tex[0] != "{":
            raise ValueError(f"String passed does not begin with '{{': {tex[:50]}, {tex.source_history.root}") # }}} <= keep lsp happy

        for index, char in enumerate(tex):
            if char == "{":
                paren_stack.append(char)
            elif char == "}":
                paren_stack.pop()
            if not paren_stack:
                return tex[1:index]
        return None

    def process(self, tex):
        """ Got lazy and didnt finish.. not even sure this class makes sense"""
        pass

#class TransformStage(Stage):
#    pass

class FilterBySectionAndMakeFlashcardsStage(BuildFlashcardStage, FilterBySectionStage):
    def __init__(self, section_names: list[str]) -> None:
        super().__init__(section_names)

    def process_chunk(self, data: TrackedString):
        """
        :param data: data as string
        :param section_names: gets all data from sections contained in section_names
        :returns list: [(name, section_contents)....] """
        flashcards = []
        counter = 0
        while counter < len(data): # check this is what i want

            if data[counter] == "%": # Do this everywhere
                comment_len = self.index_of_line_end(data[counter+1:])

                if comment_len is None:
                    raise Exception("This is probably not good... ")

                counter += comment_len
                continue

            if data[counter] != '\\':
                counter += 1
                continue

            question_match = self._find_section_titles(data[counter:])

            if question_match is None:
                counter += 1
                continue

            end_cmd_index = counter + len(question_match[0]) # index of first char after cmd
            answer_match = self._find_arg(data[end_cmd_index:])

            if answer_match is None:
                break

            # re.match start_index inclusinve but re.match end_index exclusive
#            question = data[counter:][:question_end_index]

            flashcards.append(
                    Flashcard(question_match[2],answer_match)
                    )
            counter = len(answer_match) + end_cmd_index + 1  # This sets counter equal to last character in command, +1 to move to character after command
        return flashcards

    def build(self, data: TrackedString) -> list[Flashcard]:
        logger.info(f"Calling {__class__.__name__}.process")
        chunk_flashcards = self.process_chunk(data)
        logger.debug(f"Returning {chunk_flashcards}")
        return chunk_flashcards

class FlashcardsPipeline:
    """ Generator Object
    TODO: Type hinting is kinda fucked. I have a abstract Stage class that must implement process method. Different stages can have
    different return types, so I leave it up to the user to use these stages in correct order (last stage must return list[Flashcard])
    Implementing some sort of type hinting (or class re design) to make this ordering less ambigous would be nice
    """
    def __init__(self, data_iterable: Iterable, flashcard_builder: BuildFlashcardStage, stages: list[Stage] | None = None):
        self.builder = flashcard_builder
        self.data_iterable = data_iterable
        self.stages = [] if stages is None else stages

    def __iter__(self) -> Generator[List[Flashcard], None, None]:
        for chunk in self.data_iterable:
            if chunk is None:
                yield []
            for stage in self.stages:
                chunk = stage.process(chunk)
            flashcards = self.builder.build(chunk)
            yield flashcards


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

        if match is None or match.group(0) == r'\\':
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
    logger.info(f"Calling load_macros with macros_path={macros_path}, macros_names:{macro_names}")
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
