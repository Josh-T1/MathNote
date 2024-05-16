from collections.abc import Callable
from . import utils
from pathlib import Path
from typing import Union, Tuple
import re
import logging

"""
sdjls

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


def def_flash_cards(*files: Path):
    all_sections = {}
    for file in files:
        file_contents = file.read_text()
        file_contents = remove_comments(file_contents)
        sections = get_section_contents(file_contents, ["defin"], format_callback=format_tex)
        all_sections = utils.merge_dict_list_val(all_sections, sections)
    return all_sections["defin"]


def remove_comments(tex: str):
    pattern = r'% .*?\n'
    return re.sub(pattern, '', tex)

def retreive_tex_sections(*args: Path, section_names: list[str]):
    all_contents = {}
    for arg in args:
        doc_contents = arg.read_text()
        section_contents = get_section_contents(doc_contents, section_names)
        merge_dict_list_val(all_contents, section_contents)
    return all_contents


def filter_lecture_by_sections(*args: Path, section_names: list[str]):
    all_contents = ""
    for arg in args:
        doc_contents = arg.read_text()
        filtered_doc = filter_by_section(doc_contents, section_names)
        all_contents += filtered_doc
    return all_contents

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

def _find_cmd(tex: str, macros: list[str]) -> Union[str, None]:
    """ It is assumed tex string starts with backslash character """
    for pattern in macros:
        if tex.startswith(pattern):
            return pattern
    return None

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


def remove_macros(tex: str, macros: dict[str, dict]) -> str:
    new_tex = ""
    counter = 0

    while counter < len(tex): # check this is what i want

        if tex[counter] != '\\':
            new_tex += tex[counter]
            counter += 1
            continue

        cmd = _find_cmd(tex[counter+1:], list(macros.keys()))

        if cmd == None:
            new_tex += tex[counter]
            counter += 1
            continue

        end_cmd_index = counter + len(cmd)  # -1 to accound for backslash character being in command, we want all end_*_index variables to be inclusive
        arg = _find_arg(tex[end_cmd_index +1:])

        if arg == None:
            logging.warn("Something went wrong while calling clean_self.tex")
            break

        cleaned_arg = remove_macros(arg, macros)
        new_cmd = macros[cmd]["command"].replace("#1", f" {cleaned_arg} ")

        num_brackets_ignored = 2
        new_tex += f" {new_cmd} " # Aviod issues of the from \norm{f_n}g(x) -> \lVert f_n \rVertg(x), where \rVertg(x) raises an error when compiled
        counter = len(arg) + end_cmd_index + num_brackets_ignored +1 # This sets counter equal to last character in command, +1 to move to character after command
    return new_tex

def _find_section(line: str, section_names: list[str]) -> Union[str, None]:
    """ Checks to see if macro box is present in line
    returns: string or None"""

    for section_name in section_names: #type: ignore
        pattern = rf'\\{section_name}{{.*?}}' # verify that second \\ needed or not
        match = re.search(pattern, line)
        if match:
            return match.group(0)
    return None

def filter_by_section(file_contents: str, section_names: list[str]) -> str:
    """ Retreives all latex code corresponding to section keys. ie theorem boxes
    section_names: names without backslash characater
    returns: string of latex code containge section contents and box """
    data = ""
    paranthesis_stack = []
    section_active = False

    for line in file_contents.splitlines():
        macro = _find_section(line, section_names)

        if macro != None:
            section_active = True
            line = line.replace(macro, "")
            data += macro

        char_index = 0

        while section_active and char_index <= (len(line) -1):
            char = line[char_index]
            if char == "{":
                paranthesis_stack.append(char)
            if char == "}":
                paranthesis_stack.pop()

            if not paranthesis_stack:
                section_active = False
            char_index += 1

        if char_index > 0:
            data += line[:char_index + 1] + "\n"
    return data

def find_comment(tex: str):
    for index, char in enumerate(tex):
        if char == "\n":
            return index +1
    return None

def get_section_contents(tex: str, section_names: list[str], format_callback: Union[Callable, None] = None) -> dict[str, list[Tuple]]:
    """ return: [(name, section_contents)....] """
    sections = {section_name: [] for section_name in section_names}
    counter = 0
    while counter < len(tex): # check this is what i want

        if tex[counter] == "%": # Do this everywhere
            comment_len = find_comment(tex[counter+1:])

            if comment_len == None: raise Exception

            counter += comment_len
            continue

        if tex[counter] != '\\':
            counter += 1
            continue

        match = _find_section_titles(tex[counter:], section_names)

        if match == None:
            counter += 1
            continue

        end_cmd_index = counter + len(match.group(0))
        section_contents = _find_arg(tex[end_cmd_index:])

        if section_contents == None:
            break

        if callable(format_callback):
            section_contents = format_callback(section_contents)

        formatted_section = format_tex(section_contents)
        sections[match.group(1)].append((match.group(2), formatted_section))
        counter = len(section_contents) + end_cmd_index + 1  # This sets counter equal to last character in command, +1 to move to character after command
    return sections

def _find_section_titles(line: str, section_names: list[str]): # Figure out how to have match type
    """ Checks to see if macro box is present in line
    returns: string or None"""

    for section_name in section_names: #type: ignore
        pattern = rf'^\\({section_name}){{(.*?)}}' # }}
        match = re.search(pattern, line)
        if match:
            return match
    return None

def format_tex(tex_section: str):
    lines = []
    for line in tex_section.splitlines():
        lines.append(line.lstrip("\n").lstrip())
    return "\n".join(lines)

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

def format_tex_to_mathjax(tex: str) -> str:
    macros = load_macros(MACRO_PATH, MACRO_NAMES)
    tex = remove_comments(tex)
    tex = remove_macros(tex, macros)
    mathjax = tex_to_mathjax(tex)
#    html = mathjax_to_html(mathjax)
    return tex


def format_tex(tex: str) -> str:
    macros = load_macros(MACRO_PATH, MACRO_NAMES)
    tex = remove_comments(tex)
    tex = remove_macros(tex, macros)
    return tex
