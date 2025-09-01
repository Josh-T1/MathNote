from functools import reduce
import logging
from typing import Optional, Union, Generator, List, Generic, get_args, get_origin, TypeVar
from collections.abc import Iterable
from pathlib import Path
from abc import abstractmethod, ABC

from ..models import SectionNames, SectionNamesDescriptor, Flashcard, langauage_char_registry, Section, TrackedText
from .._enums import FileType


logger = logging.getLogger("mathnote")

Input = TypeVar("Input")
Output = TypeVar("Output")


class Stage(ABC, Generic[Input, Output]):
    @abstractmethod
    def process(self, data: Input) -> Output:
        pass


class DataGenerator:
    """ Generates data in chunks. Each chunk corresponds to the contents of a file """
    def __init__(self, file_paths: list[Path]) -> None:
        super().__init__()
        self.file_paths = file_paths

    def __iter__(self) -> Generator[TrackedText | None]:
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
    """
    Stage for cleaning LaTeX/Typst code, i.e., remove comments and user defined macros

    Usage:
        macros, text = {...}, TrackedText(...)
        clean_stage = CleanStage(macros)
        cleaned_text = clean_stage.process(text)
    """
    def __init__(self, macros: dict) -> None:
        super().__init__()
        self.macros = macros
        self.char_map = None

    def process(self, data: TrackedText) -> TrackedText:
        logger.debug(f"Starting {self.process}")
        self.char_map = langauage_char_registry[data.filetype()]
        tracked_string = self._remove_comments(data)
        tracked_string = self._remove_macros(tracked_string)
        logger.debug(f"Finished {self.process}")
        return tracked_string

    def _remove_comments(self, text: TrackedText) -> TrackedText:
        assert self.char_map is not None
        pattern = fr'{self.char_map.comment} .*?\n'
        return text.sub(pattern, '')

    def _find_cmd(self, text: TrackedText, macros: list[str]) -> Union[str, None]:
        """ It is assumed tex string starts with command prefix character. e.g., '\\' in LaTeX or '#' in typst """
        for pattern in macros:
            if text.startswith(pattern) and not text[len(pattern)].isalpha(): # Not sure this covers all cases. We make sure line starts with command and next letter is not alphanumeric as that would indicate we got partial match. ie matching operator on operatorname
                return pattern
        return None

    def _find_arg(self, text: TrackedText) -> Union[TrackedText, None]:
        """ It is assume the tex string passed starts with curly bracket """
        assert self.char_map is not None
        paren_stack = []

        if str(text[0]) != self.char_map.arg_open_delim:
            raise ValueError(f"String passed does not begin with curly opening brace: {text[:50]}, {text.source}")

        for index, char in enumerate(str(text)):
            if char == self.char_map.arg_open_delim:
                paren_stack.append(char)
            elif char == self.char_map.arg_close_delim:
                paren_stack.pop()
            if not paren_stack:
                return text[1:index]
        return None

    def _remove_macros(self, text: TrackedText) -> TrackedText:
        """ Replaces all user defined macros with 'pure tex' in the sence that it would compile without a specific macros.tex/preamble.tex
        ** Limited to replacing macros of the form: \\macro_name{title}{tex}. This can not handle more complex macros
        :param tex: latex code as string
        :param macros: dictionary with key values of the form; macro_name: macro_dict_info. ie {defin: {command_in_tex: tex, ....},...}

        TODO: Currently we perform operation on TrackedText and the string representation. Change so that we only deal with one type...
        """
        assert self.char_map is not None

        text_pcs: list[TrackedText] = []
        counter: int = 0

        while counter < len(text):

            if str(text[counter]) != self.char_map.cmd_prefix:
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
            cleaned_arg = self._remove_macros(arg)
            cleaned_arg = self._add_arg_spaces(cmd_template, str(cleaned_arg))

            # TODO This only works for LaTeX
            new_cmd = cmd_template.replace("#1", str(cleaned_arg))
            num_brackets_ignored = 2

            if str(text[counter-1]).isalpha(): # Add space character to prevent joining text, however ensure previous charcater is
                new_cmd = " " + str(new_cmd)
            new_cmd += " "
            text_pcs.append(TrackedText(new_cmd, source=text.source))
            counter = len(arg) + end_cmd_index + num_brackets_ignored +1 #This sets counter equal to last character in command, +1 to move to character after command
        new_text = reduce(lambda x, y: x + y, text_pcs)
        return new_text

    def _add_arg_spaces(self, command: str, arg: str) -> str:
        if "#1" not in command: #TODO, add __contains__ for TrackedText
            return ""
        command_split = command.split("#1")
        if command_split[1][0].isalpha():
            arg += " "
        if command_split[0][-1].isalpha():
            arg = " " + arg
        return arg


# TODO: All subclasses of SectionFinder assume typst optional arg content is contained in '[]' which is not necessairly true. Look at LanguageChars, this needs to be fixed at some point
class SectionFinder(ABC):
    @abstractmethod
    def find_section(self, text: TrackedText) -> tuple[Section, int] | tuple[None, int]:
        pass

    @staticmethod
    def _content_inside_paren(text: TrackedText, paren: tuple[str, str]) -> TrackedText:
        """ It is assume the tex string passed starts paren[0] and for every opening paren we have a matching close paren """
        paren_stack = []

        if str(text[0]) != paren[0]:
            raise ValueError(f"String passed does not begin with '{paren[0]}'. Text: {text[:50]}, {text.source}") # }}} <= keep lsp happy

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

    def find_section(self, text: TrackedText) -> tuple[Section, int] | tuple[None, int]:
        char_map = langauage_char_registry[text.filetype()]
        title_paren = (char_map.arg_open_delim, char_map.arg_close_delim)
        body_paren = (char_map.opt_arg_open_delim, char_map.opt_arg_close_delim)

        is_section, member = self.is_section(text, char_map.cmd_prefix)
        if not is_section or member is None:
            return None, 0

        open_paren_index = len(member.value) + 1
        header = self._content_inside_paren(text[open_paren_index:], title_paren)
        # index relative to whole text block
        end_title_index = open_paren_index + len(header) +1 # first_curly_brace_index includes \\name{, len(title) includes {title}_, -1 to get back to }
        content = self._content_inside_paren(text[end_title_index +1:], body_paren)
        end_content_index = end_title_index + len(content) + 1 # +1 to make non inclusive. ie text[end_content_index] == a closing paren
        section: Section = {"name": member.name, "content": content, "header": header}
        return section, end_content_index


    def is_section(self, text: TrackedText, cmd_prefix: str) -> tuple[bool, SectionNamesDescriptor] | tuple[bool, None]:
        if len(text) < 2 or str(text[0]) != cmd_prefix:
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

    def find_section(self, text: TrackedText) -> tuple[Section, int] | tuple[None, int]:
        char_map = langauage_char_registry[text.filetype()]
        title_paren = (char_map.arg_open_delim, char_map.arg_close_delim)
        body_paren = (char_map.opt_arg_open_delim, char_map.opt_arg_close_delim)

        is_section, member = self.is_section(text, char_map.cmd_prefix)
        if not is_section or member is None:
            return None, 0
        # text[len(self.name + 1)] is openening bracket character

        open_paren_index = len(member.value) + 1
        header = self._content_inside_paren(text[open_paren_index:], title_paren)
        end_title_index = open_paren_index + len(header) +1 # open_paren_index includes \\name{, len(title) includes {title}_, -1 to get back to }
        content = self._content_inside_paren(text[end_title_index +1:], body_paren)

        end_content_index = end_title_index + len(content) + 1 # +1 to make non inclusive. ie text[end_content_index] == a closing paren
        section: Section = {"name": member.name, "content": content, "header": header}
        return section, end_content_index


    def is_section(self, text: TrackedText, cmd_prefix: str) -> tuple[bool, SectionNamesDescriptor | None]:
        """ We make the assumtion the only text that starts with a section name and is followd by closing curly brace
        is a valid MainSection """
        if len(text) < 2 or str(text[0]) != cmd_prefix:
            return (False, None)

        for member in self.possible_names:
            if text[1:].startswith(member.value):
                return (True, member)
        return (False, None)

class SectionBuilderStage(Stage[TrackedText, list[Section]]):
    def __init__(self):
        self.char_map = None
        self.main_section_finder = MainSectionFinder(list(SectionNames))

    def _index_of_line_end(self, text: TrackedText) -> int:
        """
        :param tex: latex code as string
        :returns int: index of line end, None if no newline character, could occur on last line in file
        """
        assert self.char_map is not None

        for index, char in enumerate(text):
            if char == self.char_map.newline:
                return index +1
        return 0

    def process(self, data: TrackedText) -> list[Section]:
        self.char_map = langauage_char_registry[data.filetype()]
        chunk = self.process_chunk(data)
        return chunk

    def process_chunk(self, data: TrackedText) -> list[Section]:
        """
        :param data: data as TrackedText
        :param section_names: gets all data from sections contained in section_names
        :returns list: [(name, section_contents)....] """
        assert self.char_map is not None

        sections: list[Section] = []
        counter: int = 0
        unamed_section: Optional[Section] = None

        while counter < len(data):

            if data[counter] == self.char_map.comment: # TODO: Adjust for typst + old note which I can no longer decifer: Do this everywhere
                comment_len = self._index_of_line_end(data[counter+1:])
                counter += comment_len
                continue

            # Add main section. i.e question, answer
            section, end_index = self.main_section_finder.find_section(data[counter:])

            if section is None:
                if unamed_section is None:
                    unamed_section = {"name": SectionNames.UNNAMED, "content": data[counter], "header": TrackedText("")}
                else:
                    unamed_section["content"] = unamed_section["content"] + data[counter]
                counter += 1
                continue

            elif section is not None and unamed_section is not None:
                sections.append(unamed_section)
                unamed_section = None

            if data.filetype() == FileType.Typst: # TODO clean this up
                section["header"] = section["header"].replace("name: ", "").replace('"', "")
            counter += end_index + 1  # This sets counter equal to last character in command, +1 to move to character after command
            sections.append(section)
        return sections


class FlashcardBuilderStage(Stage[TrackedText, List[Flashcard]]):
    def __init__(self, main_section_finder: MainSectionFinder, sub_section_finders: list[SubSectionFinder] | None = None) -> None:
        self.main_section_finder = main_section_finder
        self.sub_section_finders = [] if sub_section_finders is None else sub_section_finders
        self.char_map = None

    def _index_of_line_end(self, text: TrackedText) -> int:
        """
        :param tex: latex code as string
        :returns int: index of line end, None if no newline character, could occur on last line in file
        """
        assert self.char_map is not None
        for index, char in enumerate(text):
            if char == self.char_map.comment:
                return index +1
        return 0

    def process_chunk(self, data: TrackedText):
        """
        :param data: data as TrackedText
        :param section_names: gets all data from sections contained in section_names
        :returns list: [(name, section_contents)....] """
        assert self.char_map is not None

        flashcards: list[Flashcard] = []
        counter: int = 0
        parent_section: Optional[str] = None

        while counter < len(data): # check this is what i want

            if data[counter] == self.char_map.comment: # TODO: Adjust for typst + old note which I can no longer decifer: Do this everywhere
                comment_len = self._index_of_line_end(data[counter+1:])
                counter += comment_len
                continue

            # add subsections to flashcard
            if parent_section:
                for subsection_finder in self.sub_section_finders:
                    if parent_section not in subsection_finder.parents:
                        continue
                    section, end_index = subsection_finder.find_section(data[counter:])
                    if section != None:
                        flashcards[-1].add_info(section["name"], section["content"])
                        counter += end_index

            # Add main section. i.e question, answer
            section, end_index = self.main_section_finder.find_section(data[counter:])

            if section is None:
                counter += 1
                continue

            parent_section = section["name"] # the command title. e.g \defin{...}{...}

            if data.filetype() == FileType.Typst: # TODO clean this up
                section["header"] = section["header"].replace("name: ", "").replace('"', "")
            flashcards.append(
                    Flashcard(section["name"], section["header"], section["content"])
                    )
            counter += end_index + 1  # This sets counter equal to last character in command, +1 to move to character after command
        return flashcards

    def process(self, data: TrackedText) -> list[Flashcard]:
        self.char_map = langauage_char_registry[data.filetype()]
        logger.debug(f"Calling {self.__class__.__name__}.process")
        chunk_flashcards = self.process_chunk(data)
#        chunk_flashcards = self.re_format_flashcards(chunk_flashcards)
        logger.debug(f"Returning {repr(chunk_flashcards)}")
        return chunk_flashcards

    def add_subsection_finder(self, subsection_finder: SubSectionFinder):
        self.sub_section_finders.append(subsection_finder)

#    def re_format_flashcards(self, flashcards: list[Flashcard]):
#        for flashcard in flashcards:
#            if len(flashcard.question) > 4
#            # TODO: refacator Flashcardsor not hasattr(flashcard, "proof"):
#                continue
#            flashcard.question = flashcard.answer
#            flashcard.answer = flashcard.proof # refactor flashcard to fix this
#        return flashcards

class ProcessingPipeline(Generic[Output]):
    def __init__(self, data_iterable: Iterable):
        self.data_iterable = data_iterable
        self.stages: list[Stage] = []
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

    def __iter__(self) -> Generator[list[Output], None, None]:
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
