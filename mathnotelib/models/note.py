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

    def remove_tag(self, tag: str) -> None:
        if tag in (tags:=self.metadata.tags):
            tags.remove(tag)

    def add_tag(self, tag: str) -> None:
        self.metadata.add_tag(tag)

@dataclass
class Note(SourceFile):
    """ Model of note """
    metadata: Metadata
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

    def tags(self, all: bool=False) -> set:
        """Returns note tags
        Args:
            all: bool, default False
                if True note inherits all tags from parent categories
        Returns:
            set of tags
        """
        tags = self.metadata.tags.copy()
        if not all:
            cat = self.category
            while cat:
                tags.union(cat.metadata.tags)
                cat = cat.parent
        return self.metadata.tags

    def remove_tag(self, tag: str) -> None:
        if tag in (tags:=self.metadata.tags):
            tags.remove(tag)

    def add_tag(self, tag: str) -> None:
        self.metadata.tags.add(tag)
