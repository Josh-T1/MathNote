from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
from typing import Optional

class OutputFormat(Enum):
    PDF = "pdf"
    SVG = "svg"

class FileType(Enum):
    Typst = "Typst"
    LaTeX = "LaTeX"
    Unsupported = "Unsupported"

@dataclass
class TypsetFile:
    path: Path

    def file_type(self) -> FileType:
        map = {".tex": FileType.LaTeX, ".typ": FileType.Typst}
        return map.get(self.path.suffix, FileType.Unsupported)
