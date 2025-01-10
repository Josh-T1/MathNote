from pathlib import Path
import json
import platform
import os

TEMPLATES_PATH = Path(__file__).parent / "templates"

def config_dir():
    if os.name == "nt":
        config_dir = Path(os.getenv("APPDATA")) / "mathnote"
    elif os.name == "posix":
        config_dir = Path.home() / ".config" / "mathnote"
    else:
        raise OSError("Unsupported operating system")
    return config_dir

class LatexCompilationError(Exception):
    pass

def open_cmd() -> str:
    """
    Returns the open command for the respective operating system
    """
    system_name = platform.system().lower()
    if system_name == "darwin":
        cmd = "open"
    elif system_name == "linux":
        cmd = "xdg-open"
    else:
        cmd = "start"
    return cmd

def save_config(config: dict):
    cf_path = config_dir()
    if cf_path.is_dir():
        with open(cf_path, "w") as f:
            json.dump(config, f, indent=6)

def load_json(file: str):
    with open(file, "r") as f:
        contents = json.load(f)
    return contents

def dump_json(file: str, contents: str):
    with open(file, "w") as f:
        json.dump(contents, f)

class SectionNamesDescriptor:
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value

    def __get__(self, instance, owner=None):
        return self
    def __str__(self):
        return self.value

class ImmutableMeta(type):
    _is_initialized = False

    def __new__(mcs, name, bases, class_dict):
        user_enum_key_values = {key.upper(): value for key, value in config['section-names'].items()}
        class_dict.update(user_enum_key_values)
        for key, value in class_dict.items():
            if not key.startswith("__"):
                class_dict[key] = SectionNamesDescriptor(key, value)
        cls = super().__new__(mcs, name, bases, class_dict)
        cls._is_initialized = True
        return cls

    def is_name(cls, name:str) -> bool:
        for attr_name in cls.__dict__:
            if name == attr_name:
                return True
        return False

    def __iter__(cls):
        for attr_name in cls.__dict__:
            attr_value = getattr(cls, attr_name)
            if isinstance(attr_value, SectionNamesDescriptor):
                yield attr_value

    def __setattr__(cls, key, value):
        if cls._is_initialized and key in cls.__dict__:
            raise AttributeError(f"Cannot modify attribute '{key}'. SectionNames attributes are immutable.")
        super().__setattr__(key, value)

    def __iterable__(cls):
        return cls

    def __contains__(cls, value):
        if isinstance(value, str):
            return value in [i.value for i in cls]
        elif isinstance(value, SectionNamesDescriptor):
            return value.value in [i.value for i in cls]
        else:
            return False


class SectionNames(metaclass=ImmutableMeta):
    DEFINITION = "defin"
    THEOREM = "theo"
    DERIVATION = "der"
    PROOF = "pf"
    COROLLARY = "corollary"
    LEMMA = "lemma"
    PROPOSITION = "proposition"


def get_config() -> dict:
    """ Checks for user defined config, otherwise sets some default settings """
    config = {"root": str(Path.home() / "Notes"),
              "main-template": "" ,
              "macros-path": "",
              "preamble-path": "" ,
              "note-macros-path": "",
              "note-preamble-path": "",
              "assignment-template": "",
              "course_info_template": str(TEMPLATES_PATH/ "course_info_template.json"),
              "macro-names": [],
              "section-names": {}
              }
    files = [
            ("main-template", "main_template.tex"),
            ("macros-path","macros.tex"),
            ("preamble-path","preamble.tex"),
            ("note-macros-path","note_macros.tex"),
            ("note-preamble-path","note_preamble.tex"),
            ("assignment-template","assignment-template.tex")
            ]
    cf_path = config_dir()
    if cf_path.is_dir():
        with open(cf_path / "config.json", 'r') as f:
            config.update(json.load(f))

        for key, file_name in files:
            if (cf_path / file_name).is_file():
                config[key] = str(cf_path / file_name)
            else:
                config[key] = str(TEMPLATES_PATH / file_name)

    return config

config = get_config()
