from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from .source_file import SourceFile


@dataclass
class Category:
    """
    Acts as node with child Categories and notes
    """
    path: Path
    notes: list["Note"]
    parent: Optional['Category'] = None
    metadata: dict = field(default_factory=dict)

    def __eq__(self, other):
        if not isinstance(other, Category):
            return False
        return self.path == other.path
    def __post_init__(self):
        assert self.path.exists() and self.path.is_dir()

    def pretty_name(self) -> str:
        return self.name.replace("_", " ").replace("-", " ")

    @property
    def name(self) -> str:
        return self.path.stem


@dataclass
class Note(SourceFile):
    """ Model of note """
    category: Category

    def pretty_name(self) -> str:
        return self.name.replace("_", " ").replace("-", " ")

    def __eq__(self, other):
        if not isinstance(other, Note):
            return False
        return other.name == self.name and self.category == other.category

    @property
    def name(self) -> str:
        return self.path.stem

