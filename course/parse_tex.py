from collections.abc import Callable
from os import stat
from . import utils
from pathlib import Path
from typing import Union, Tuple, Any
import re
import logging
from abc import abstractmethod, ABC
from dataclasses import dataclass

"""
This module needs re working and testing

"""

"""
Tex

"""
MACRO_PATH = utils.get_config()["macros-path"]
MACRO_NAMES = ["mlim", "norm", "squarebk", "roundbk", "curlybk", "anglebk", "abs", "operator", "rline",
               "uline"]

TEX_PATTERN_TO_MATHJAX = {r"\\begin\{equation\*\}": r"\[",
                        r"\\end\{equation\*\}": r"\]",
                        ">": "&gt;",
                        "<": "&lt;",
                        "&": "&amp;",
                          }

@dataclass
class FlashCard:
    question: str
    answer: str


class EmptyFlashCard(FlashCard):
    def __init__(self, message: str) -> None:
        super().__init__(question=message, answer=message)
# Macros needs to be re thought.


class Stage(ABC):
    @abstractmethod
    def process(self, data):
        pass

class GetDataStage(Stage):
    def __init__(self, file_paths: list[Path]) -> None:
        super().__init__()
        self.file_paths = file_paths
        self.file_contents = ""

    def _load_file_contents(self):
        for file in self.file_paths:
            file_contents = file.read_text(encoding='utf-8')
            self.file_contents += file_contents

    def process(self, data=None):
        self._load_file_contents()
        return self.file_contents

class CleanStage(Stage):
    def __init__(self, macros: dict) -> None:
        super().__init__()
        self.macros = macros

    def process(self, data):
        data = self.remove_comments(data)
        data = self.remove_macros(data)
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
            raise ValueError(f"String passed does not begin with curly opeining brace: {tex}")

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
                    FlashCard(match.group(2),section_contents)
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


