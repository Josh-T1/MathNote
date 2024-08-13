from abc import ABC, abstractmethod
from pathlib import Path
import re
from typing import Union, Tuple
import logging

logger = logging.getLogger(__name__)

class LatexParser(ABC):
    @abstractmethod
    def parse(self) -> str:
        pass

class MacroParser(LatexParser):
    def __init__(self, macros_path, macro_names, tex) -> None:
        super().__init__()
        self.tex: str = tex
        self.macros_path: Path = macros_path
        self._macros: Union[None, dict] = None
        self.macro_names: list[str] = macro_names # Make this dynamic at some point

    @property
    def macros(self) -> dict[str,dict]:
        r""" Gets all user commands from self.macros_path
        Macros beign parsed have the form:
            \macro_name{name(optional)}{
                something(optional)
                }
        returns: dict of the form {cmd_name: {args: #, tex_cmd: ""}}
        """
        if self._macros:
            return self._macros

        macros = dict()
        document = Path(self.macros_path).read_text().splitlines()
        pattern = r'\\newcommand\{(.*?)\}\[(.*?)\]'
        # Makes assumtion that the only characters in 'line' are part of command with the exception of whitespace
        for line in document:
            match = re.search(pattern, line)

            if not match:
                continue
            name = match.group(1)

            if name in self.macro_names:
                tex_cmd = line.replace(match.group(0), "").strip()[1:-1] # remove enclosing curly braces
                macros[name] = {"num_args": match.group(2), "command": tex_cmd}
        return macros

    def _find_cmd(self, tex: str) -> Union[str, None]:
        """ It is assumed tex string starts with backslash character """
        for pattern in self.macros:
            if tex.startswith(pattern):
                return pattern
        return None

    def _find_arg(self, tex) -> Union[Tuple[str, int], Tuple[None, None]]:
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
                return tex[1:index], index + 1
        return None, None


    def parse(self) -> str:
        new_tex = ""
        counter = 0
        num_chars = len(self.tex)

        while counter < num_chars:

            if self.tex[counter] != "\\":
                new_tex += self.tex[counter]
                counter += 1
                continue

            cmd = self._find_cmd(self.tex[counter:])

            if cmd == None:
                new_tex += self.tex[counter]
                counter += 1
                continue

            end_cmd_index = counter + len(cmd) - 1 # -1 to accound for backslash character being in command, we want all end_*_index variables to be inclusive
            arg, end_index = self._find_arg(self.tex[end_cmd_index + 1:])

            if arg == None or end_index == None:
                logging.warn("Something went wrong while calling clean_self.tex")
                break

            cleaned_arg = self.parse(arg)
            new_cmd = self.macros[cmd]["command"].replace("#1", f" {cleaned_arg} ")

            new_tex += f" {new_cmd} " # Aviod issues of the from \norm{f_n}g(x) -> \lVert f_n \rVertg(x), where \rVertg(x) raises an error when compiled
            counter = end_index + end_cmd_index + 1  # This sets counter equal to last character in command, +1 to move to character after command
        return new_tex
