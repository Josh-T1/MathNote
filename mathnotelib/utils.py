from pathlib import Path
import json
import platform
import os
import shutil

templates_path= Path(__file__).parent / "templates"

def config_dir():
    if os.name == "nt":
        config_dir = Path(os.getenv("APPDATA")) / "MathNote"
    elif os.name == "posix":
        config_dir = Path.home() / ".config" / "MathNote"
    else:
        raise OSError("Unsupported operating system")
    return config_dir

def get_config() -> dict:
    """ Checks for user defined config, otherwise sets some default settings """
    config = {
            "root": str(Path.home() / "MathNote"),
            "preamble-path": "" ,
            "course-info-template": str(templates_path/ "course_info_template.json"),
            "macro-names": [],
            "section-names": {},
            "iterm2-enabled": False,
            "set-note-title": True
            }
    files = [
            ("main-template", "main_template.tex"),
            ("assignment-template","assignment_template.tex"),
            ("problems-template","problems_template.tex"),
            ("note-template", "note_template.tex"),
            ("macros","macros.tex"),
            ("preamble","preamble.tex"),
            ("note-macros","note_macros.tex"),
            ("note-preamble","note_preamble.tex")
            ]
    cf_path = config_dir()
    if cf_path.is_dir():
        with open(cf_path / "config.json", 'r') as f:
            config.update(json.load(f))

        for key, file_name in files:
            if (cf_path / file_name).is_file():
                config[key] = str(cf_path / file_name)
            else:
                config[key] = str(templates_path / file_name)

    return config

config = get_config()


# TODO should be 'LaTeX'
class LatexCompilationError(Exception):
    pass

class TypstCompilationError(Exception):
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

# TODO update to support typst
def update_config():
    """
    Users may specify latex templates in config directory. These templates are copied into the required directories when
    cli.py is ran for the first time. If a user changes a template, this function must be called, otherwise nothing changes.
    """
    root = Path(config["root"])
    macros, preamble = Path(config["macros"]), Path(config["preamble"])
    note_macros, note_preamble = Path(config["note-macros"]), Path(config["note-preamble"])
    shutil.copy(macros, root / "macros.tex")
    shutil.copy(preamble, root / "preambles.tex")
    shutil.copy(note_macros, root / "Notes/resources/macros.tex")
    shutil.copy(note_preamble, root / "Notes/resources/preamble.tex")


def load_json(file: str):
    with open(file, "r") as f:
        contents = json.load(f)
    return contents

def dump_json(file: str, contents: str):
    with open(file, "w") as f:
        json.dump(contents, f)

def rendered_sorted_key(path: Path):
    num = int(path.name.split(".")[0].split("-")[1])
    return num
