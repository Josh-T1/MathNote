from pathlib import Path
import shutil
import os
import re
import json
from typing import Optional
from dataclasses import dataclass, field

from .enums import FileType

@dataclass(frozen=True)
class Section:
    name: str
    patterns: dict[FileType, str]
    parents: frozenset[str] = field(default_factory=frozenset)

    @property
    def requires_parent(self) -> bool:
        return len(self.parents) > 0

    def to_dict(self) -> dict:
        return {
                "patterns": {ftype.name: ptrn for ftype, ptrn in self.patterns.items()},
                "parents": sorted(self.parents)
                }

    @classmethod
    def from_dict(cls, name: str, data: dict) -> "Section":
        patterns = {FileType[k]: v for k, v in data["patterns"].items()}
        parents = frozenset(data.get("parents", []))
        return cls(name=name, patterns=patterns, parents=parents)


class Config:
    """Singleton class that stores global configuration for the MathNote app"""
    _instance: Optional["Config"]=None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    # Should we even take args?
    def __init__(self, root_path: Path | None = None):
        """
        Args:
            root_path: Root directory for MathNote data
            templates_path: Directory containing all template files (i.e., templates_path/LaTeX(Typst)/{template}.tex(typ))
            macro_names: List of macro names used in typestting projects
            log_level: Logging level
            template_files: Dict: filetype -> (template_name -> template_path). Maps filetype to a a new map, which maps template name to template path
            editor: Default editor to open files, nvim and vim are the only supported options
        """

        if getattr(self, "_initizialized", False): return
        self._initizialized = True

        if isinstance(root_path, Path) and root_path.is_dir():
            self.root_path = root_path
        else:
            self.root_path = Path.home() / "MathNote"

        self.decks_dir = self.root_path / "Decks"
        self.note_repo_dir = self.root_path / "NoteRepositories"
        self.templates_path = Path(__file__).parent / "templates"

        self.log_level = "DEBUG"
        self.template_files: dict[FileType, dict[str, Path]] = {}
        self.section_names: dict[str, Section] = {}
        self.macro_names = [] # TODO delete
        self.macros: dict[FileType, dict[str, str]] = {}

        self.typst_packages: dict[str, list] = {"local": list(), "global": list()}
        self.latex_packages: list[str] = []

        self._load_config_from_json()

    def _load_config_from_json(self):
        """ Updates default values with values specified in config file """
        config_dir = self.config_dir()
        if not config_dir.is_dir():
            raise EnvironmentError("Environment was incorrectly initialized, missing config directory")

        config_path = config_dir / "config.json"
        if not config_path.is_file():
            raise EnvironmentError("Environment was incorrectly initialized, missing config file")
        # The issue here is the loaded values are str not objects
        with open(config_path, 'r') as f:
            data = json.load(f)

        if "root" in data and (dir := Path(data["root"])).is_dir():
            self.root_path = dir
        else:
            raise EnvironmentError(f"Root directory '{data["root"]}' does not exist")

        if "section-names" in data:
            self.section_names = {
                    name: Section.from_dict(name, sec_data) for name, sec_data in data["section-names"].items()
                    }

        if "macro-names" in data:
            self.macro_names = data["macro-names"]

        if "log-level" in data:
            self.log_level = data["log-level"]
        if "Typst-packages" in data:
            self.typst_packages = data["typst-packages"]
        if "LaTeX-packages" in data:
            self.latex_packages = data["LaTeX-packages"]

        files = [
                "main_template",
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
        self.macros = self._load_macros()

    @classmethod
    def config_dir(cls):
        """
        Returns:
            platform-specific user config directory
        Raises:
            OSError: if operating system is unsupported
        """
        if os.name == "nt":
            config_dir = Path(os.getenv("APPDATA")) / ".config" / "MathNote"
        elif os.name == "posix":
            config_dir = Path.home() / ".config" / "MathNote"
        else:
            raise OSError("Unsupported operating system")
        return config_dir

    def update_templates(self):
        """Copies templates from user config directory to app templates directory"""
        # TODO test
        for file_type, ext in [(FileType.LaTeX, ".tex"), (FileType.Typst, ".typ")]:
            macros_path = self.template_files[file_type]["macros"]
            preamble_path = self.template_files[file_type]["preamble"]
            note_macros_path = self.template_files[file_type]["note_macros"]
            note_preamble_path = self.template_files[file_type]["note_preamble"]

            shutil.copy(macros_path, self.templates_path / file_type.value / f"macros{ext}")
            shutil.copy(preamble_path, self.templates_path / file_type.value / f"preamble{ext}")
            shutil.copy(note_macros_path, self.templates_path / file_type.value / f"note_macros{ext}")
            shutil.copy(note_preamble_path, self.templates_path / file_type.value / f"note_preamble{ext}")

    # TODO validate parents
    def save(self):
        config_path = self.config_dir() / "config.json"
        data = {
            "root": str(self.root_path),
            "section-names": {
                name: section.to_dict() for name, section in self.section_names.items()
            },
            "macro-names": self.macro_names,
            "typst-packages": self.typst_packages,
            "latex-packages": self.latex_packages,
            "log-level": self.log_level,
        }
        config_path.write_text(json.dumps(data, indent=2))

    @staticmethod
    def cache_dir():
        return Config.config_dir() / "cache"

    # this aint it
    def _load_macros(self) -> dict[FileType, dict[str, str]]:
        r""" Gets all user commands from macro_path
        Macros beign parsed have the form:
            \newcommand{macro name}[nargs(int)]{
                command
                }
        returns: dict of the form {cmd_name: {args: #, tex_cmd: ""}}
        """
        tex_path = self.template_files[FileType.LaTeX]["macros"]
        typst_path = self.template_files[FileType.Typst]["macros"]
        if tex_path.is_file():
            tex_doc = tex_path.read_text().splitlines()
            tex_macros = self._parse_latex_macros(tex_doc)
        else:
            # TODO: LOg
            tex_macros = {}
            print(f"Failed to load LaTeX macros, file {tex_path} does not exist")

        if typst_path.is_file():
            typst_doc = typst_path.read_text().splitlines()
            typst_macros = self._parse_typst_macros(typst_doc)
        else:
            typst_macros = {}
            print(f"Failed to load Typst macros, file {typst_path} does not exist")
        return {FileType.Typst: typst_macros, FileType.LaTeX: tex_macros}


    def _parse_latex_macros(self, lines: list[str]) -> dict[str, str]:
        macros = dict()
        pattern = r'\\newcommand\{(.*?)\}\[(.*?)\]'
        # Makes assumtion that the only characters in 'line' are part of command with the exception of whitespace
        for line in lines:
            match = re.search(pattern, line)

            if not match:
                continue
            name = match.group(1).lstrip("\\")

            if name in self.macro_names:
                tex_cmd = line.replace(match.group(0), "").strip()[1:-1] # remove enclosing curly braces
                macros[name] = {"num_args": match.group(2), "command": tex_cmd}
        return macros


    def _parse_typst_macros(self, lines: list[str]) -> dict:
        #TODO: for now we just import required packages (probably better solution anyways)
        return {}


# TODO delete
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


CONFIG = Config()
