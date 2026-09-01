from pathlib import Path
import os
import re
import json
from typing import Optional
from dataclasses import dataclass, field
import platform
import subprocess
from .enums import FileType
import logging

logger = logging.getLogger(__name__)

def _typst_data_dir() -> Path:
    """Ask the typst binary directly for its package path — most robust."""
    try:
        result = subprocess.run(
            ["typst", "info"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        for line in result.stdout.splitlines():
            if line.strip().lower().startswith("package path"):
                path_str = line.split(":", 1)[1].strip()
                return Path(path_str)
    except (subprocess.SubprocessError, FileNotFoundError, IndexError):
        pass

    # fallback: platform convention table
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ["APPDATA"])
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:  # Linux and other Unix
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "typst" / "packages"

def typst_package_dir(package: "TypstPackage") -> Path:
    if package.namespace != "local":
        raise NotImplementedError(
            f"Resolving non-local Typst packages ('{package.namespace}') is not yet supported"
        )
    return _typst_data_dir() / "local" / package.name / package.version

@dataclass(frozen=True)
class TypstPackage:
    name: str
    version: str
    namespace: str = "local"
    is_default: bool = False
    is_macro: bool = False

    @property
    def import_target(self) -> str:
        return f"@{self.namespace}/{self.name}:{self.version}"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "namespace": self.namespace,
            "default": self.is_default,
            "is-macro": self.is_macro
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TypstPackage":
        return cls(
            name=data["name"],
            version=data["version"],
            namespace=data.get("namespace", "local"),
            is_default=data.get("default", False),
            is_macro=data.get("is-macro", False)
        )

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

    def __init__(self, root_path: Path | None = None):
        """  """
        if getattr(self, "_initizialized", False): return
        self._initizialized = True

        if isinstance(root_path, Path) and root_path.is_dir():
            self.root_path = root_path
        else:
            self.root_path = Path.home() / "MathNote"

        self.decks_dir = self.root_path / "Decks"
        self.note_repo_dir = self.root_path / "NoteRepositories"
        self.courses_dir = self.root_path / "Courses"
        self.templates_path = Path(__file__).parent / "templates"
        self.typst_preamble_path = None
        self.typst_macro_path = None
        self.latex_macro_path = self.root_path / "Preambles" / "macros.tex"
        self.latex_preamble_path = self.root_path / "Preambles" / "preamble.tex"
        self.enable_exp_export = False

        self.log_level = "DEBUG"
        self.template_files: dict[FileType, dict[str, Path]] = {}
        self.section_names: dict[str, Section] = {}
        self.typst_packages: list[TypstPackage] = []

        self._load_config_from_json()
        self._validate_and_set_defaults()


    def _validate_and_set_defaults(self):
        flagged_macro = [pkg for pkg in self.typst_packages if pkg.is_macro is True]
        if len(flagged_macro) == 1:
            self.typst_macro_path = typst_package_dir(flagged_macro[0])
        elif len(flagged_macro) > 1:
            raise EnvironmentError(f"Multiple Typst packages configured as macro")

        flagged_default = [pkg for pkg in self.typst_packages if pkg.is_default is True]

        if len(flagged_default) == 1:
            self.typst_preamble_path = typst_package_dir(flagged_default[0])
        elif len(flagged_default) > 1:
            raise EnvironmentError("Multiple Typst packages set to default")

        if not self.latex_preamble_path.is_file():
            logger.warning(f"LaTeX preamble path {self.latex_preamble_path} does not exist")

        if not self.latex_macro_path.is_file():
            logger.warning(f"LaTeX macro path {self.latex_macro_path} does not exist")

        if self.typst_preamble_path is None or (self.typst_preamble_path is not None and not self.typst_preamble_path.exists()):
            logging.warning("Invalid or non existant typst preamble package")

        if self.typst_macro_path is None or (self.typst_macro_path is not None and not self.typst_macro_path.exists()):
            logging.warning("Invalid or non existant typst macro package")

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

        if "log-level" in data:
            self.log_level = data["log-level"]

        if "typst-packages" in data:
            for pkg_data in data["typst-packages"]:
                self.typst_packages.append(TypstPackage.from_dict(pkg_data))

        if "enable-experimental-export" in data:
            self.enable_exp_export = data['enable-experimental-export']
        files = [
                "main_template",
                "assignment_template",
                "note_template",
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
            config_dir = Path(os.getenv("APPDATA")) / ".config" / "MathNote"
        elif os.name == "posix":
            config_dir = Path.home() / ".config" / "MathNote"
        else:
            raise OSError("Unsupported operating system")
        return config_dir


    # TODO validate parents
    def save(self):
        config_path = self.config_dir() / "config.json"
        data = {
            "root": str(self.root_path),
            "section-names": {
                name: section.to_dict() for name, section in self.section_names.items()
            },
            "typst-packages": [
                pkg.to_dict() for pkg in self.typst_packages
                ],
            "typst-macros": None,
            "log-level": self.log_level,
            "enable-experimental-export": self.enable_exp_export
        }
        config_path.write_text(json.dumps(data, indent=2))

    @staticmethod
    def cache_dir():
        return Config.config_dir() / "cache"

    def set_log_level(self, level: str):
        self.log_level = level
        level = getattr(logging, level)
        logging.getLogger().setLevel(level)

CONFIG = Config()

class MacroParser:
    def __init__(self):
        self._cache: dict[FileType, dict] = {FileType.LaTeX: {}, FileType.Typst: {}}

    def parse_macros(self) -> dict[FileType, dict]:
        if len(self._cache[FileType.Typst]) == 0:
            self._cache[FileType.Typst] = self._parse_typst()
        if len(self._cache[FileType.LaTeX]) == 0:
            self._cache[FileType.LaTeX] = self._parse_latex()
        return self._cache

    def _parse_latex(self) -> dict[str, dict]:
        macros = {}

#        pattern = r'\\newcommand\{(.*?)\}\[(.*?)\]'
        if CONFIG.latex_macro_path is None:
            return macros
        text = CONFIG.latex_macro_path.read_text()
        # matches only the header: \newcommand{name}[nargs]{  -- stops right after the opening body brace
        header_pattern = re.compile(r'\\newcommand\{\\?(\w+)\}\[(\d+)\]\{')

        for match in header_pattern.finditer(text):
            name = match.group(1)
            num_args = match.group(2)

            body_start = match.end()  # position right after the opening '{'
            body_end = self._find_matching_brace(text, body_start)
            if body_end is None:
                continue  # malformed / unbalanced — skip rather than crash

            command = text[body_start:body_end]
            macros[name] = {"num_args": num_args, "command": command}

        return macros


    def _find_matching_brace(self, text: str, open_pos: int) -> int | None:
        """
        Given a position in `text` right after an opening '{' has already been
        consumed by the caller, scan forward tracking nested braces and return
        the index of the matching closing '}'. Returns None if unbalanced.
        """
        depth = 1  # we've already consumed one '{' (the one at open_pos - 1)
        i = open_pos
        while i < len(text):
            char = text[i]
            if char == '\\' and i + 1 < len(text):
                i += 2  # skip escaped characters like \{ \} so they don't affect depth
                continue
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return None

    def _parse_typst(self) -> dict[str, dict]:
        macros = {}
        if CONFIG.typst_macro_path is None:
            return macros
        text = CONFIG.latex_macro_path.read_text()
        # matches: #let name(args) = {   -- stops right after the opening body brace
        header_pattern = re.compile(r'#let\s+(\w+)\(([^)]*)\)\s*=\s*\{')

        for match in header_pattern.finditer(text):
            name = match.group(1)
            params = match.group(2)

            body_start = match.end()
            body_end = self._find_matching_brace(text, body_start)
            if body_end is None:
                continue

            command = text[body_start:body_end].strip()
            num_args = len([p for p in params.split(',') if p.strip()])
            macros[name] = {"num_args": str(num_args), "params": params, "command": command}

        return macros


MACROS = MacroParser()
