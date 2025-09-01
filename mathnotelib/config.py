from dataclasses import dataclass, field
from pathlib import Path
import json
import shutil
import os

from ._enums import FileType

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

