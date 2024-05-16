from enum import CONFORM
from pathlib import Path
import json

CONFIG_PATH = Path(__file__).parent.parent / "config.json"

def load_json(path: Path):
    with open(path, "r") as f:
        val = json.load(f)
    return val

def dump_json(path: Path, dic: dict):
    with open(path, "w") as f:
        json.dump(dic, f, indent=6)

def get_config():
    return load_json(CONFIG_PATH)

def save_config(updated_config: dict):
    dump_json(CONFIG_PATH, updated_config)

def number2filename(n: int):
    return 'lec_{0:02d}.tex'.format(n)

def filename2number(s: int):
    return int(str(s).replace('.tex', '').replace('lec_', ''))

def merge_dict_list_val(dict1, dict2):
    """ dicts of the form {key: list} """
    all_keys = dict2.keys() | dict1.keys()
    for key in all_keys:
        if key not in dict1:
            dict1[key] = dict2[key]
        elif key in dict2:
            dict1[key].extend(dict2[key])
    return dict1

@staticmethod
def parse_command_macro(line) -> str:
    r""" Assumes first character in line is opening curly brace only one sections enclosed by {}.
    Only works when command is of the form {\right\cmd{#1}\left}. Will fail if its of the form
    {\right\cmd{#1}{}\left}. ie each nested {} must be preceeded by backslash.
    """
    counter, num_sections = 0, 1
    paren_stack, command_paren_stack = [], []
    data = ""
    command = False

    for char in line:
        # When command equals true we want to append char to string
        if command == True and char == "}":
            paren_stack.pop()
            data += char
            command = False

        elif command == True and (char == '{' or char == '['):
            command_paren_stack.append(char)
            data += char

        elif command == True and (char == '}' or char == ']'):
            command_paren_stack.pop()
            data += char

        # When command equals False we do not want opening or closing brackets as these seperate sections
        elif char == "{" or char == '[':
            paren_stack.append(char)

        elif char == "}" or char == ']':
            paren_stack.pop()

        else:
            # We allow nested {} if preceeded by \
            if char == "\\":
                command = True
            data += char
        # Paren stack is empty if and only if we are onto a new section
        if not paren_stack:
            counter += 1

        if counter == num_sections:
            return data
    return data
