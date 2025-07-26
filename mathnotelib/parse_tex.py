import json
import re
from functools import reduce
import logging
from typing import Iterable, SupportsIndex, Union, Generator, List, Callable, Generic, TypeVar, get_args, get_origin
from pathlib import Path
from abc import abstractmethod, ABC
from dataclasses import dataclass, field

from .utils import SectionNamesDescriptor, config
from .structure import FileType

logger = logging.getLogger("mathnote")

"""
parse_tex.py aims to provide a customizable pipeline that takes in file paths (.tex files) and returns 'cleaned' tex. This cleaned latex code can then
be utilized to build Flashcards objects

1. Get macro names dynamically
"""

MACRO_PATH = config["macros"]

class TrackedText:
    def __init__(self, text: str, source: Path | None = None):
        self.text = text
        self.source = source

    def join(self, iterable: Iterable["TrackedText"]):
        if not iterable:
            return TrackedText("")
        joined_text = self.text.join([str(tracked_text) for tracked_text in iterable])
        return TrackedText(joined_text, source = self.source)

    def __getitem__(self, __key) -> 'TrackedText':
        return TrackedText(self.text.__getitem__(__key), source=self.source)

    def filetype(self) -> FileType:
        suffix_map = {".typ": FileType.Typst, ".tex": FileType.LaTeX}
        if self.source is None:
            return FileType.Unsupported
        return suffix_map.get(self.source.suffix, FileType.Unsupported)

    def apply_func(self, func: Callable[[str], str]): #replace instances of modify text with this
        new_text = func(self.text)
        return TrackedText(new_text)
    def sub(self, pattern: str, repl: str) -> 'TrackedText':
        new_text = re.sub(pattern, repl, self.text)
        return TrackedText(new_text, source=self.source)
    def encode(self, encoding: str = 'utf-8', errors: str = 'strict'):
        return self.text.encode(encoding=encoding, errors=errors)
    def __bool__(self):
        return len(self.text) != 0
    def __add__(self, other: 'TrackedText'):
        """
        Other must be of type TrackedText and be of the same file type

        Left add has priority except for the special case where the string on the left has None as source. e.g.,

        T1 = TrackedText(...)
        T2 = TrackedText(...)
        result = T1 + T2

        Then result has source property equal to T1.source
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
    def __str__(self):
        return self.text
    def __iter__(self): # Should this iterate over self.text str chars or TrackedText(char)?
        return self.text.__iter__()
    def __len__(self):
        return len(self.text)
    def __repr__(self):
        return (f"TrackedText({self.text}, self.source={self.source})")
    def startswith(self, prefix: str | tuple[str, ...], *args) -> bool:
        return self.text.startswith(prefix, *args)
    def isalpha(self) -> bool:
        return self.text.isalpha()


@dataclass
class Flashcard:
    section_name: str
    question: TrackedText
    answer: TrackedText
    pdf_answer_path: None | str = None
    pdf_question_path: None | str = None
    additional_info: dict = field(default_factory=dict)
    seen: bool = False

    def filetype(self) -> FileType:
        return self.question.filetype()

    def add_info(self, name: str, info: str):
        self.additional_info[name] = info

    def __repr__(self):
        question = "..." if self.question else 'None'
        answer = "..." if self.answer else 'None'
        return f"Flashcard(question={question}, answer={answer}, pdf_answer_path={self.pdf_question_path}, pdf_question_path={self.pdf_answer_path}, file_type={self.filetype()})"

    def __str__(self):
        return f"Flashcard(question={self.question}, answer={self.answer}, pdf_answer_path={self.pdf_question_path}, pdf_question_path={self.pdf_answer_path})"

Input = TypeVar("Input")
Output = TypeVar("Output")

class Stage(ABC, Generic[Input, Output]):
    @abstractmethod
    def process(self, data: Input) -> Output:
        pass

class FlashcardCache:
    def __init__(self, cache_dir: Path):
        super().__init__()
        self.cache_dir = cache_dir
        self._cache = {}
        self._section_names = None

    @property
    def section_names(self):
        return self._section_names

    @section_names.setter
    def section_names(self, section_names: list[SectionNamesDescriptor]):
        self._section_names = sorted([section_name.value for section_name in section_names])

    @property
    def cache(self):
        if not self._cache:
            self._cache = self._load_cache()
        return self._cache

    def _load_cache(self):
        cache = {}
        for file in self.cache_dir.iterdir():
            if file.is_file():
                cache[file.name] = str(file)
        return cache

    def load_from_cache(self, path: str):
        with open(path, "r") as f:
            json.load(f)

    def cache_key(self, path: Path) -> str | None:
        if self.section_names is None:
            return None
        key = "-".join(self.section_names) + str(path)
        return key

    def get_cache(self, path: Path):
        cache_key = self.cache_key(path)
        filename = self.cache.get(cache_key, None)
        if filename is not None:
            cache_value = self.load_from_cache(filename)
            return cache_value
        return None

class DataGenerator:
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

            return_value = TrackedText(file_contents, source=file_path)
            yield return_value

class CleanStage(Stage[TrackedText, TrackedText]):
    def __init__(self, macros: dict) -> None:
        super().__init__()
        self.macros = macros

    def process(self, data: TrackedText) -> TrackedText:
        logger.debug(f"Starting {self.process}")
        tracked_string = self.remove_comments(data)
        tracked_string = self.remove_macros(tracked_string)
        logger.debug(f"Finished {self.process}")
        return tracked_string


    def remove_comments(self, text: TrackedText) -> TrackedText:
        pattern = r'% .*?\n'
        return text.sub(pattern, '')

    def _find_cmd(self, text: TrackedText, macros: list[str]) -> Union[str, None]:
        """ It is assumed tex string starts with backslash character """
        for pattern in macros:
            if text.startswith(pattern) and not text[len(pattern)].isalpha(): # Not sure this covers all cases. We make sure line starts with command and next letter is not alphanumeric as that would indicate we got partial match. ie matching operator on operatorname
                return pattern
        return None

    @staticmethod
    def _find_arg(text: TrackedText) -> Union[TrackedText, None]:
        """ It is assume the tex string passed starts with curly bracket """
        print(text.source, "source")
        print(text.filetype())
        paren = ("{", "}") if text.filetype() == FileType.LaTeX else ("[", "]") # TODO -currently no handling of unsupported

        paren_stack = []

        if str(text[0]) != paren[0]: # } <- this comment is to keep vim lsp happy
            raise ValueError(f"String passed does not begin with curly opening brace: {text[:50]}, {text.source}")

        for index, char in enumerate(str(text)):
            if char == paren[0]:
                paren_stack.append(char)
            elif char == paren[1]:
                paren_stack.pop()
            if not paren_stack:
                return text[1:index]
        return None

    def remove_macros(self, text: TrackedText) -> TrackedText:
        """ Replaces all user defined macros with 'pure tex' in the sence that it would compile without a specific macros.tex/preamble.tex
        ** Limited to replacing macros of the form: \\macro_name{title}{tex}. This can not handle more complex macros
        :param tex: latex code as string
        :param macros: dictionary with key values of the form; macro_name: macro_dict_info. ie {defin: {command_in_tex: tex, ....},...}
        """
        text_pcs: list[TrackedText] = []
        counter: int = 0

        while counter < len(text):

            if text[counter] != '\\':
                text_pcs.append(text[counter])
                counter += 1
                continue

            cmd = self._find_cmd(text[counter+1:], list(self.macros.keys()))

            if cmd == None:
                text_pcs.append(text[counter])
                counter += 1
                continue

            end_cmd_index = counter + len(cmd)  # -1 to accound for backslash character being in command, we want all end_*_index variables to be inclusive
            arg = self._find_arg(text[end_cmd_index +1:])

            if arg is None:
                logging.warn("Something went wrong while calling clean_self.tex")
                break

            cmd_template = self.macros[cmd]["command"]
            cleaned_arg = self.remove_macros(arg)
            cleaned_arg = self.add_arg_spaces(cmd_template, cleaned_arg)

            new_cmd = cmd_template.replace("#1", cleaned_arg)
            num_brackets_ignored = 2

            if str(text[counter-1]).isalpha(): # Add space character to prevent joining text, however ensure previous charcater is
                new_cmd = " " + new_cmd
            new_cmd += " "
            text_pcs.append(TrackedText(new_cmd, source=cleaned_arg.source))
            counter = len(arg) + end_cmd_index + num_brackets_ignored +1 #This sets counter equal to last character in command, +1 to move to character after command
        new_text = reduce(lambda x, y: x + y, text_pcs)
        return new_text

    def add_arg_spaces(self, command: TrackedText, arg: TrackedText) -> TrackedText:
        if "#1" not in command:
            return TrackedText("")
        command_split = command.split("#1")
        if command_split[1][0].isalpha():
            arg += TrackedText(" ")
        if command_split[0][-1].isalpha():
            arg = reduce(lambda x, y: x + y, command_split)
        return arg

@dataclass
class Section:
    header: TrackedText
    content: TrackedText
    name: str
    end_index: int


class SectionFinder(ABC):
    @abstractmethod
    def find_section(self, text: TrackedText) -> Section | None:
        pass

    @staticmethod
    def _content_inside_paren(text: TrackedText, paren: tuple[str, str]) -> TrackedText:
        """ It is assume the tex string passed starts paren[0] and for every opening paren we have a matching close paren """
        paren_stack = []

        if str(text[0]) != paren[0]:
            raise ValueError(f"String passed does not begin with '{paren[0]}': {text[:50]}, {text.source}") # }}} <= keep lsp happy

        for index, char in enumerate(str(text)):
            if char == paren[0]:
                paren_stack.append(char)
            elif char == paren[1]:
                paren_stack.pop()
            if not paren_stack:
                return text[1:index]
        raise ValueError("Invalid string")

class SubSectionFinder(SectionFinder):
    def __init__(self, parents):
        super().__init__()
        self.parents = parents

class ProofSectionFinder(SubSectionFinder):
    def __init__(self, names: SectionNamesDescriptor | list[SectionNamesDescriptor], parent_names: list[SectionNamesDescriptor]):
        super().__init__([parent.name for parent in parent_names])
        self.section_name_members = names if isinstance(names, list) else [names]

    def find_section(self, text: TrackedText) -> Section | None:
        title_paren = ("{", "}") if text.filetype() == FileType.LaTeX else ("(", ")") # TODO -currently no handling of unsupported
        body_paren = ("{", "}") if text.filetype() == FileType.LaTeX else ("[", "]") # TODO -currently no handling of unsupported

        section, member = self.is_section(text)
        if not section or not member:
            return None
        open_paren_index = len(member.value) + 1
        header = self._content_inside_paren(text[open_paren_index:], title_paren)
        # index relative to whole text block
        end_title_index = open_paren_index + len(header) +1 # first_curly_brace_index includes \\name{, len(title) includes {title}_, -1 to get back to }
        content = self._content_inside_paren(text[end_title_index +1:], body_paren)
        end_content_index = end_title_index + len(content) + 1 # +1 to make non inclusive. ie text[end_content_index] == a closing paren
        return Section(header, content, member.name, end_content_index)


    def is_section(self, text: TrackedText) -> tuple[bool, SectionNamesDescriptor | None]:
        if len(text) < 2:
            return (False, None)
        for member in self.section_name_members:
            if text[1:].startswith(member.value):
                return (True, member)
        return (False, None)


class MainSectionFinder(SectionFinder):
    r"""
    Finds sections of the form:

    e.g., LaTeX
    \cmd{name}{
            content
            }

    e.g., Typst
    #cmd(title: name)[
            content
            ]
    """
    def __init__(self, names: list[SectionNamesDescriptor] | SectionNamesDescriptor):
        """
        -- Params --
        names: list of section names. Should probably convert to list[SectionNames]
        """
        self.possible_names = names if isinstance(names, list) else [names]

    def find_section(self, text: TrackedText) -> None | Section:
        title_paren = ("{", "}") if text.filetype() == FileType.LaTeX else ("(", ")") # TODO -currently no handling of unsupported
        body_paren = ("{", "}") if text.filetype() == FileType.LaTeX else ("[", "]") # TODO -currently no handling of unsupported

        is_section, member = self.is_section(text)
        if not is_section or member is None:
            return None
        # text[len(self.name + 1)] is openening bracket character
        open_paren_index = len(member.value) + 1
        header = self._content_inside_paren(text[open_paren_index:], title_paren)
        # index relative to whole text block
        end_title_index = open_paren_index + len(header) +1 # open_paren_index includes \\name{, len(title) includes {title}_, -1 to get back to }
        content = self._content_inside_paren(text[end_title_index +1:], body_paren)
        end_content_index = end_title_index + len(content) + 1 # +1 to make non inclusive. ie text[end_content_index] == a closing paren
        return Section(header, content, member.name, end_content_index)

    def is_section(self, line: TrackedText) -> tuple[bool, SectionNamesDescriptor | None]:
        """ We make the assumtion the only text that starts with a section name and is followd by closing curly brace
        is a valid MainSection """
        if len(line) < 2:
            return (False, None)

        for member in self.possible_names:
            if line[1:].startswith(member.value):
                return (True, member)
        return (False, None)

class BuilderStage(Stage[TrackedText, List[Flashcard]]):
    def __init__(self, main_section_finder: MainSectionFinder, sub_section_finders: list[SubSectionFinder] | None = None) -> None:
        self.main_section_finder = main_section_finder
        self.sub_section_finders = [] if sub_section_finders is None else sub_section_finders

    @staticmethod
    def index_of_line_end(text: TrackedText) -> int | None:
        """
        :param tex: latex code as string
        :returns int: index of line end, None if no newline character, could occur on last line in file
        """
        for index, char in enumerate(text):
            if char == "\n":
                return index +1
        return None

    def process_chunk(self, data: TrackedText):
        """
        :param data: data as TrackedText
        :param section_names: gets all data from sections contained in section_names
        :returns list: [(name, section_contents)....] """
        # The issue is data has no source
        cmd_char = '\\' if data.filetype() == FileType.LaTeX else "#" # TODO - currently not handling unsported
        flashcards = []
        counter = 0
        parent_section = None
        while counter < len(data): # check this is what i want

            if data[counter] == "%": # TODO: Adjust for typst + old note which I can no longer decifer: Do this everywhere
                comment_len = self.index_of_line_end(data[counter+1:])

                if comment_len is None:
                    raise Exception("This is probably not good... ")

                counter += comment_len
                continue
            if str(data[counter]) != cmd_char:
                counter += 1
                continue
            # add subsections to flashcard
            if parent_section:
                for subsection_finder in self.sub_section_finders:
                    if parent_section not in subsection_finder.parents:
                        continue
                    match = subsection_finder.find_section(data[counter:])
                    if match != None:
                        flashcards[-1].add_info(match.name, match.content)
                        counter += match.end_index

            # Add main section. i.e question, answer
            section = self.main_section_finder.find_section(data[counter:])

            if section is None:
                counter += 1
                continue
            parent_section = section.name # the command title. e.g \defin{...}{...}
            if data.filetype() == FileType.Typst: # TODO clean this up
                section.header = TrackedText(str(section.header).replace("name: ", "").replace('"', ""), source=data.source)
            flashcards.append(
                    Flashcard(section.name, section.header, section.content)
                    )
            counter += section.end_index + 1  # This sets counter equal to last character in command, +1 to move to character after command
        return flashcards

    def process(self, data: TrackedText) -> list[Flashcard]:
        #check types

        logger.debug(f"Calling {__class__.__name__}.process")
        chunk_flashcards = self.process_chunk(data)
#        chunk_flashcards = self.re_format_flashcards(chunk_flashcards)
        logger.debug(f"Returning {repr(chunk_flashcards)}")
        return chunk_flashcards

    def add_subsection_finder(self, subsection_finder: SubSectionFinder):
        self.sub_section_finders.append(subsection_finder)

    def re_format_flashcards(self, flashcards: list[Flashcard]):
        for flashcard in flashcards:
            if len(flashcard.question) > 4 or not hasattr(flashcard, "proof"):
                continue
            flashcard.question = flashcard.answer
            flashcard.answer = flashcard.proof # refactor flashcard to fix this
        return flashcards

class FlashcardsPipeline:
    def __init__(self, data_iterable: Iterable):
        self.data_iterable = data_iterable
        self.stages = []
        self.last_output_type = None

    def add_stage(self, stage: Stage):
        # TODO make sure first stage takes valid input
        stage_type = type(stage)
        input_type, output_type = None, None
        for base in getattr(stage_type, "__orig_bases__", []):
            if get_origin(base) is Stage:
                input_type, output_type = get_args(base)
                break
        if input_type is None or output_type is None:
            raise TypeError("Stage must subclass Stage[Input, Output]")

        if len(self.stages) != 0 and self.last_output_type != input_type:
            raise TypeError(f"Incompatible stage: expected input {self.last_output_type}, got {input_type}")
        self.stages.append(stage)
        self.last_output_type = output_type

    def __iter__(self) -> Generator[List[Flashcard], None, None]:
        valid = get_origin(self.last_output_type) == list and get_args(self.last_output_type) == (Flashcard,)
        if not valid:
            raise TypeError(f"Invalid pipeline: expected last stage output type to be List[Flashcard], got {self.last_output_type}")

        for chunk in self.data_iterable:
            if chunk is None:
                yield []
                continue
            for stage in self.stages:
                chunk = stage.process(chunk)
            yield chunk


def find_math_mode(tex: str):
    """ This has erros. For some reason it matches double backslash """
    inline_match = re.match(r"^\\\(.*?\\\)", tex)

    if inline_match != None:
        return inline_match

    return re.match(r"^\\[.*?\\]", tex)


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
