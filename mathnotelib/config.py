from dataclasses import dataclass, field
from pathlib import Path
import json
import shutil
import os
from typing import Optional

from ._enums import FileType


class Config:
    """Singleton class that stores global configuration for the MathNote app"""
    _instance: Optional["Config"]=None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self,
                 macro_names: list[str] | None=None,
                 section_names: dict[str, str] | None=None,
                 log_level: str = "INFO",
                 iterm2_enabled: bool = False,
                 set_note_title: bool = True,
                 template_files: dict[FileType, dict[str, Path]] | None=None ,
                 editor: str = "vim",
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
        self.root_path = Path.home() / "MathNote"
        self.templates_path = Path(__file__).parent / "templates"
        self.macro_names = macro_names if macro_names is not None else []
        self.section_names = section_names if section_names is not None else {}
        self.log_level = log_level
        self.iterm2_enabled = iterm2_enabled
        self.set_note_title = set_note_title
        self.template_files = template_files if template_files is not None else {}
        self.editor = editor

    def __post_init__(self):
        """Updates default values with values specified in config file"""
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
        """
        Returns:
            platform-specific user config directory
        Raises:
            OSError: if operating system is unsupported
        """
        if os.name == "nt":
            config_dir = Path(os.getenv("APPDATA")) / "MathNote"
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


CONFIG = Config()
