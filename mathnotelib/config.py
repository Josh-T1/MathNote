from pathlib import Path
import json
import shutil
import os
import re
from typing import Optional

from ._enums import FileType


class Config:
    """Singleton class that stores global configuration for the MathNote app"""
    _instance: Optional["Config"]=None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    # Should we even take args?
    def __init__(self,
#                 macro_names: list[str] | None=None,
#                 section_names: dict[str, str] | None=None,
                 log_level: str = "INFO",
                 iterm2_enabled: bool = False,
                 set_note_title: bool = True,
                 editor: str = "vim",
                 root_path: Path | None = None,
                 ):
        """
        Args:
            root_path: Root directory for MathNote data
            templates_path: Directory containing all template files (i.e., templates_path/LaTeX(Typst)/{template}.tex(typ))
            macro_names: List of macro names used in typestting projects
            section_names: Mapping of section names to their abbreviations
            log_level: Logging level
            iterm2_enabled: If set to true additional iterm2 functinality is enabled. Default iterm2_enabled=False
            template_files: Dict: filetype -> (template_name -> template_path). Maps filetype to a a new map, which maps template name to template path
            editor: Default editor to open files, nvim and vim are the only supported options
        """

        if getattr(self, "_initizialized", False):
            return
        self._initizialized = True

        if isinstance(root_path, Path) and root_path.is_dir:
            self.root_path = root_path
        else:
            self.root_path = Path.home() / "MathNote"

        self.templates_path = Path(__file__).parent / "templates"
        self.macro_names = []
#        self.section_names = section_names if section_names is not None else {}
        self.log_level = log_level
        self.iterm2_enabled = iterm2_enabled
        self.set_note_title = set_note_title
        self.template_files: dict[FileType, dict[str, Path]] = {}
        self.editor = editor

        self.typst_packages: list[str] = []
        self.latex_packages: list[str] = []
        # tmp - add to config
        self.section_names: dict[str, dict[str, str]] = {
                "DEFINITION": {
                    FileType.LaTeX.value: "defin",
                    FileType.Typst.value: "definition"
                    },
                "THEOREM": {
                    FileType.LaTeX.value: "theo",
                    FileType.Typst.value: "theorem"
                    },
                "PROOF": {
                    FileType.LaTeX.value: "pf",
                    FileType.Typst.value: "proof"
                    },
                "COROLLARY": {
                    FileType.LaTeX.value: "corollary",
                    FileType.Typst.value: "corollary"
                    },
                "LEMMA": {
                    FileType.LaTeX.value: "lemma",
                    FileType.Typst.value: "proposition"
                    },
                "PROPOSITION": {
                    FileType.LaTeX.value: "proposition",
                    FileType.Typst.value: "proposition"
                    },
                "UNAMED": {
                    FileType.LaTeX.value: "unamed",
                    FileType.Typst.value: "unamed"
                    },
                }

        self._macros: dict[FileType, dict] | None = None
        self._update_config()

    def _update_config(self):
        """ Updates default values with values specified in config file """
        config_dir = self.config_dir()
        if not config_dir.is_dir():
            raise EnvironmentError("Environment was incorrectly initialized, missing config directory")

        config_path = config_dir / "config.json"
        if not config_path.is_file():
            raise EnvironmentError("Environment was incorrectly initialized, missing config file")

        with open(config_path, 'r') as f:
            data = json.load(f)
            for k, v in data.items():
                if not isinstance(v, bool) and not isinstance(v, int) and not v: # skip emtpy entries
                    continue
                if hasattr(self, k):
                    setattr(self, k, v)

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

    @classmethod
    def config_dir(cls):
        # TODO allow for root_dir?
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

    @staticmethod
    def cache_dir():
        return Config.config_dir() / "cache"

    def macros(self) -> dict[FileType, dict[str, dict]]:
        r""" Gets all user commands from macro_path
        Macros beign parsed have the form:
            \newcommand{macro name}[nargs(int)]{
                command
                }
        returns: dict of the form {cmd_name: {args: #, tex_cmd: ""}}
        """
        if self._macros is not None:
            return self._macros

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
        self._macros = {FileType.Typst: typst_macros, FileType.LaTeX: tex_macros}
        return self._macros


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

CONFIG = Config()


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
