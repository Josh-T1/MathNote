from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from .source_file import SourceFile

@dataclass
class Metadata:
    tags: set = field(default_factory=set)

    def to_dict(self):
        return {"tags": list[self.tags]}

    def add_tag(self, tag: str):
        self.tags.add(tag)

@dataclass
class Category:
    """
    Acts as node with child Categories and notes
    """
    metadata: Metadata
    path: Path
    notes: list["Note"]
    parent: Optional['Category'] = None

    def __post_init__(self):
        assert self.path.exists() and self.path.is_dir()

    @property
    def name(self) -> str:
        return self.path.stem

    def remove_tag(self, tag: str) -> None:
        if tag in (tags:=self.metadata.tags):
            tags.remove(tag)

    def add_tag(self, tag: str) -> None:
        self.metadata.add_tag(tag)

@dataclass
class Note(SourceFile):
    """ TODO """
    metadata: Metadata
    category: Category

    def global_metadata(self):
        cat = self.category
        tags = self.metadata.tags.copy()
        while cat:
            tags.union(cat.metadata.tags)
            cat = cat.parent
        return Metadata(tags)

    @property
    def name(self) -> str:
        return self.path.stem

    def tags(self) -> set:
        return self.metadata.tags

    def remove_tag(self, tag: str) -> None:
        if tag in (tags:=self.metadata.tags):
            tags.remove(tag)

    def add_tag(self, tag: str) -> None:
        self.metadata.tags.add(tag)
