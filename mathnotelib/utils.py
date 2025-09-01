from dataclasses import dataclass, field
from pathlib import Path
import json
import os
import shutil
from enum import Enum
import platform

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

class FileType(Enum):
    Typst = "Typst"
    LaTeX = "LaTeX"
    Unsupported = "Unsupported"

@dataclass
class Config:
    root_path: Path = Path.home() / "MathNote"
    templates_path: Path = Path(__file__).parent / "templates"
    macro_names: list[str] = field(default_factory=list)
    section_names: dict[str, str] = field(default_factory=dict)
    log_level: str = "INFO"
    iterm2_enabled: bool = False
    set_note_title: bool = True
    template_files: dict[FileType, dict[str, Path]] = field(default_factory=dict)
    editor: str = "vim"

    def __post_init__(self):
        config_dir = self.config_dir()
        if not config_dir.is_dir():
            return
        config_path = config_dir / "config.json"
        if not config_path.is_file():
            return

        with open(config_path, 'r') as f:
            data = json.load(f)
            for k, v in data.items():
                if not isinstance(v, bool) and not isinstance(v, int) and not v: # skip emtpy entries
                    continue
                if hasattr(self, k):
                    setattr(self, k, v)
        files = ["main_template",
                "assignment_template",
                "problems_template",
                "note_template",
                "macros",
                "preamble",
                "note_macros",
                "note_preamble"
                ]

        for file_type, ext in {FileType.LaTeX: "tex", FileType.Typst: "typ"}.items():
            self.template_files[file_type] = {}
            for file_stem in files:
                file_path = config_dir / file_type.value / f"{file_stem}.{ext}"
                if file_path.is_file():
                    self.template_files[file_type][file_stem] = file_path
                else:
                    template_path = self.templates_path / file_type.value / f"{file_stem}.{ext}"
                    self.template_files[file_type][file_stem] = template_path

    @classmethod
    def config_dir(cls):
        if os.name == "nt":
            config_dir = Path(os.getenv("APPDATA")) / "MathNote"
        elif os.name == "posix":
            config_dir = Path.home() / ".config" / "MathNote"
        else:
            raise OSError("Unsupported operating system")
        return config_dir

    def update_templates(self):
        # TODO test
        for file_type, ext in [(FileType.LaTeX, "tex"), (FileType.Typst, "typ")]:
            macros_path = self.template_files[file_type]["macros"]
            preamble_path = self.template_files[file_type]["preamble"]
            note_macros_path = self.template_files[file_type]["note_macros"]
            note_preamble_path = self.template_files[file_type]["note_preamble"]

            shutil.copy(macros_path, self.templates_path / file_type.value / f"macros.{ext}")
            shutil.copy(preamble_path, self.templates_path / file_type.value / f"preamble.{ext}")
            shutil.copy(note_macros_path, self.templates_path / file_type.value / f"note_macros.{ext}")
            shutil.copy(note_preamble_path, self.templates_path / file_type.value / f"note_preamble.{ext}")


CONFIG = Config()

class LaTeXCompilationError(Exception):
    pass


class TypstCompilationError(Exception):
    pass


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
        user_enum_key_values = {key.upper(): value for key, value in CONFIG.section_names.items()}
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


# TODO: This solution sucks
# Warning: we dynamically set attr 'proof' using the value of SectionNames.PROOF
class SectionNames(metaclass=ImmutableMeta):
    DEFINITION = "defin"
    THEOREM = "theo"
    DERIVATION = "der"
    PROOF = "proof"
    COROLLARY = "corollary"
    LEMMA = "lemma"
    PROPOSITION = "proposition"
    UNNAMED = "unnamed"
    PREAMBLE = "preamble"


def load_json(file: str):
    with open(file, "r") as f:
        contents = json.load(f)
    return contents

def dump_json(file: str, contents: str) -> None:
    with open(file, "w") as f:
        json.dump(contents, f)

def rendered_sorted_key(path: Path) -> int:
    num = int(path.name.split(".")[0].split("-")[1])
    return num
