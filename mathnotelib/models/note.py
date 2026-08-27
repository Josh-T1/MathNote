from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from collections.abc import MutableMapping
import json

from .source_file import SourceFile

class PersistentMetadata(MutableMapping):
    def __init__(self, path: Path):
        self._path = path
        self._data: dict = json.loads(path.read_text()) if path.exists() else {}

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value
        self._write()

    def __delitem__(self, key):
        del self._data[key]
        self._write()

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def _write(self):
        self._path.write_text(json.dumps(self._data))

@dataclass
class Category:
    """
    Acts as node with child Categories and notes
    """
    path: Path
    notes: list["Note"]
    metadata: PersistentMetadata
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

