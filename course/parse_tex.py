from collections.abc import Callable
from . import utils
import time
from pathlib import Path
from typing import Union,  Any
import re
import logging
from abc import abstractmethod, ABC
from dataclasses import dataclass
import copy
from ..global_utils import get_config

logger = logging.getLogger(__name__)

MACRO_PATH = get_config()["macros-path"]


# TODO:  load these in a more dynmaic way
MACRO_NAMES = ["mlim", "norm", "squarebk", "roundbk", "curlybk", "anglebk", "abs", "operator", "rline",
               "uline", "mylist"]

# this is unfinished as I realized I do not need to convert tex to mathjax. Could be usefull eventually tho
TEX_PATTERN_TO_MATHJAX = {r"\\begin\{equation\*\}": r"\[",
                        r"\\end\{equation\*\}": r"\]",
                        ">": "&gt;",
                        "<": "&lt;",
                        "&": "&amp;",
                          }

class SourceRecord:
    """
    Wrapper for abstract 'Node' object in a linked list.
    Stores data related to the source of a string  """
    def __init__(self, data: str):
        self.data = data
        self.parent: None | SourceRecord = None
        self.child: None | SourceRecord = None
    def __str__(self):
        return f"SourceRecord({self.data})"
    def __repr__(self) -> str:
        parent_exists = 'Yes' if self.parent else 'No'
        child_exists = 'Yes' if self.child else 'No'
        return (f"SourceRecord({self.data},"
                f"parent={parent_exists},"
                f"child={child_exists})")

class SourceHistory:
    """
    Wrapper for linked list datastructre.
    Container for SourceRecord objects """
    def __init__(self, *args):
        self.root: None | SourceRecord = None
        for arg in args:
            self.append(arg)

    def append(self, data):
        new_node = SourceRecord(data)
        if self.root is None:
            self.root = new_node
        else:
            current = self.root
            while current.child:
                current = current.child

            current.child = new_node
            new_node.parent = current

    def append_and_copy(self, item: SourceRecord):
        """ Issues may arise if item.data is mutable """
        new_source = SourceHistory()
        current = self.root
        while current:
            new_source.append(current.data)
            current = current.child
        new_source.append(item.data)
        return new_source

    def __iter__(self):
        current = self.root
        while current:
            yield current.data
            current = current.child
    def __repr__(self):
        return f"SourceHistory({list(self)})"
    def __str__(self):
        return '->'.join(event for event in self)
    def __add__(self, other):
        if not isinstance(other, SourceHistory):
            raise TypeError(f"Unsupported opperand type(s) for +: 'SourceHistory' and '{type(other)}'")
        current = other.root
        while current:
            self.append(current.data)
            current.child
        return self # does this make sense?

class TrackedString(str):
    """
    TrackedString tries to use 'duck typing' by implementing all behaviour associated with strings, with additional features such
    as storing souce data. This data could look like a file_path or the name of a callable that 'created' the string.


    --- Limitations:
        1. We give priority to left TrackedString. If string = TrackedString1(...) + TrackedString2(...) string.source_history will only contain
        the history of TrackedString1(...). This asserts there will always be exactly one 'root' source at the expense of tracking 'all' sources
        2. ...
    """

    def __new__(cls, string,  source_history=None):
        instance = super().__new__(cls, string)
        if isinstance(source_history, SourceHistory):
            pass
        elif isinstance(source_history, str):
            record = SourceRecord(source_history)
            source_history = SourceHistory()
            source_history.append(record)
        elif source_history is None:
            source_history = SourceHistory("None")
        else:
            raise TypeError(f"Invalid source_history type: {type(source_history)}")

        instance._source_history = source_history
        return instance

    def __init__(self, string: str, source_history: SourceHistory) -> None:
        self._source_history = source_history

    @property
    def source_history(self):
        return copy.deepcopy(self._source_history)

    def __getitem__(self, __key) -> 'TrackedString':
        new_source_history = self._source_history.append_and_copy(
                SourceRecord(f"__getitem__({__key})")
                )
        return TrackedString(super().__getitem__(__key), source_history=new_source_history)

    def modify_text(self, func: Callable[[str], str]):
        """  Delete this method ? """
        new_text = func(self.__str__())
        new_source_history = SourceRecord(func.__name__)
        return TrackedString(new_text,
                             source_history=self._source_history.append_and_copy(new_source_history)
                             )
    def sub(self, pattern: str, repl: str) -> "TrackedString":
        new_text = re.sub(pattern, repl, self.__str__())
        new_source = self._source_history.append_and_copy(SourceRecord(f"re.sub({pattern}, {repl}, {self.__str__()})"))
        return TrackedString(new_text, new_source)

    def __add__(self, other):
        """ Left add has priority. If result = TrackedString1(...) + TrackedString2(...), result.source_history.parent = TrackedString1(...) """
        if not isinstance(other, str):
            raise TypeError(f"Other must be type str not type {type(other)}")
        other_text = other if not isinstance(other, TrackedString) else other.__str__()
        new_source = self._source_history.append_and_copy(SourceRecord(f"{self} + {other}"))
        return TrackedString(super().__str__() + other_text,
                             source_history=new_source)


    def __contains__(self, string: str):
        return super().__contains__(string)

    def __len__(self):
        return super().__len__()

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

    def __str__(self) -> str:
        return super().__str__()

    def __repr__(self):
        return (f"TrackedString({super().__repr__()}, self._source_history=SourceHistory(...))")

    def __getattr__(self, name):
        return getattr(super(), name)

    def lower(self):
        return super().lower()

    def upper(self):
        return super().upper()


@dataclass
class Flashcard:
    """ Remove error message.. first check all instances in project """
    question: str
    answer: str
    error_message: str = ""
    pdf_answer_path: None | str = None
    pdf_question_path: None | str = None
    seen: bool = False

    def __str__(self):
        # TODO fix this, defining all these variables is retarted
        question = "Yes" if self.question else 'No'
        answer = "Yes" if self.answer else 'No'
        pdf_question_path = "Yes" if self.pdf_question_path else 'No'
        pdf_answer_path = "Yes" if self.pdf_answer_path else 'No'
        return f"Flashcard(question={question}, answer={answer}, pdf_answer_path={pdf_answer_path}, pdf_question_path={pdf_question_path})" #Blindly using repr() as suggested by chat gpt to escape characters.. that has never created issues for me

class EmptyFlashcard(Flashcard):
    """ I beleive this can be deleted... Ensure all instance have been removed from project"""
    def __init__(self) -> None:
        super().__init__(question="", answer="", error_message="No flashcards available to display")


class Stage(ABC):
    @abstractmethod
    def process(self, data):
        pass

class GetDataStage(Stage):
    def __init__(self, file_paths: list[Path]) -> None:
        super().__init__()
        self.file_paths = file_paths
        self.file_contents = []

    def _load_file_contents(self):
        for file_path in self.file_paths:
            try:
                file_contents = file_path.read_text(encoding='utf-8')
            except Exception as e:
                logger.error(f"Failed to read file {file_path}\n{e}")
                return

            source_history = SourceHistory(str(file_path))
            self.file_contents.append(
                    TrackedString(file_contents, source_history=source_history)
                    )
            print(self.file_contents[-1].source_history)
        logger.debug(f"Finished loading file contents: {self.file_contents}")

    def process(self, data=None) -> list[TrackedString]:
        logger.info(f"Starting {__class__.__name__}.process")
        self._load_file_contents()
        return self.file_contents

class CleanStage(Stage):
    def __init__(self, macros: dict) -> None:
        super().__init__()
        self.macros = macros

    def process(self, data: list[TrackedString]) -> list[TrackedString]:
        logger.info(f"Starting {__class__.__name__}.process")
        new_data = []
        for tracked_string in data:
            start_time = time.time()
            tracked_string = self.remove_comments(tracked_string)
            logger.debug(f"Tooook {time.time() - start_time}")
            start_time = time.time()
            tracked_string = self.remove_macros(tracked_string)
            logger.debug(f"Tooook {time.time() - start_time}")
            new_data.append(tracked_string)
        logger.debug(f"Finished cleaning data, returning {new_data}")
        return new_data


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
        new_tex = TrackedString("", source_history=None) #type: ignore
        counter = 0

        while counter < len(tex): # check this is what i want

            if tex[counter] != '\\':
                new_tex = TrackedString(str(new_tex) + str(tex[counter]), source_history=tex[counter].source_history)
                counter += 1
                continue

            cmd = self._find_cmd(tex[counter+1:], list(self.macros.keys()))

            if cmd == None:
                new_tex = TrackedString(str(new_tex)+ str(tex[counter]), source_history=tex[counter].source_history)
                new_tex = tex[counter] + new_tex # have to be carefull when adding TrackedString's... a sign of good design
                counter += 1
                continue

            end_cmd_index = counter + len(cmd)  # -1 to accound for backslash character being in command, we want all end_*_index variables to be inclusive
            arg = self._find_arg(tex[end_cmd_index +1:])

            if arg is None:
                logging.warn("Something went wrong while calling clean_self.tex")
                break

            cleaned_arg = self.remove_macros(arg)
            new_cmd = self.macros[cmd]["command"].replace("#1", f" {cleaned_arg} ")
            num_brackets_ignored = 2
            new_tex = TrackedString(str(new_tex) + f" {new_cmd} ", cleaned_arg.source_history)# Hack solution to ensure TrackedString.source_history.root is correct
            counter = len(arg) + end_cmd_index + num_brackets_ignored +1 # This sets counter equal to last character in command, +1 to move to character after command
        return new_tex

class FilterStage(Stage):
    """ This is where I can filter doc by section.
    Untested and unfinished.. """
    def __init__(self, section_names: list[str]) -> None:
        super().__init__()
        self.section_names = section_names

    def process(self, tex):
        return tex

class FilterBySectionStage(FilterStage):
    def __init__(self, section_names: list[str]) -> None:
        super().__init__(section_names)

    def _find_section_titles(self, line: TrackedString): # Figure out how to have match type
        """ Checks to see if macro box is present in line
        returns: string or None"""

        for section_name in self.section_names: #type: ignore
            pattern = rf'^\\({section_name}){{(.*?)}}' # }}
            match = re.search(pattern, line)
            if match:
                return match
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

    def process(self, tex):
        pass

class TransformStage(Stage):
    pass

class FilterBySectionAndMakeFlashcardsStage(FilterBySectionStage):
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

            match = self._find_section_titles(data[counter:])

            if match is None:
                counter += 1
                continue

            end_cmd_index = counter + len(match.group(0))
            section_contents = self._find_arg(data[end_cmd_index:])

            if section_contents is None:
                break

            question_start_index, question_end_index = match.start(2), match.end(2)
            # re.match start_index inclusinve but re.match end_index exclusive
            question = data[counter:][question_start_index:question_end_index]

            flashcards.append(
                    Flashcard(question,section_contents)
                    )
            counter = len(section_contents) + end_cmd_index + 1  # This sets counter equal to last character in command, +1 to move to character after command
        return flashcards

    def process(self, data: list[TrackedString]):
        logger.info(f"Calling {__class__.__name__}.process")
        flashcards = []
        for chunk in data:
            chunk_flashcards = self.process_chunk(chunk)
            flashcards.extend(chunk_flashcards)
        logger.debug(f"Returning {flashcards}")
        return flashcards

class FlashcardsPipeline:
    def __init__(self, stages: list[Stage]):
        self.stages = stages

    def run(self) -> Any:
        logger.info(f"Calling {__class__.__name__}.process")
        data = []
        for stage in self.stages:
            data = stage.process(data)
        logger.debug(f"Returning {data}")
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
