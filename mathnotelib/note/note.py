from pathlib import Path
import json
import shutil
import subprocess
from mathnotelib.utils import open_cmd, config
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

ROOT_DIR = Path(config['root'])

# wtf is this
PROTECTED = ["resources"]

class NoteType(Enum):
    LaTeX = "LaTeX"
    Typst = "Typst"

@dataclass
class Metadata:
    tags: set = field(default_factory=set)

    def to_json(self):
        return {"tags": list[self.tags]}


@dataclass
class Category:
    """
    Category continaing a 'Tree' of child notes and child categories
    """
    metadata: Metadata
    path: Path
    children: List["Category"] = field(default_factory=list)
    parent: Optional["Category"] = None
    notes: List["Note"] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.path.stem

    def remove_tag(self, tag: str) -> None:
        if tag in (tags:=self.metadata.tags):
            tags.remove(tag)
            self.write_metadata()

    def add_tag(self, tag: str) -> None:
        self.metadata.tags.add(tag)
        self.write_metadata()

    def write_metadata(self):
        d = self.metadata.to_json()
        with (self.path / "cat-metadata.json").open("w") as f:
            json.dump(d, f, indent=2)

    def get_subcategory(self, path: Path) -> Optional["Category"]:
        res = None
        for child in self.children:
            if child.path.resolve() == path.resolve():
                return child
            else:
                res = child.get_subcategory(path)

        return res

@dataclass
class Note(ABC):
    """
    Container for .tex/.typ file and all auxilary files and metadata, e.g tags
    path: Full path to note (file)
    """
    path: Path
    local_metadata: Metadata
    category: Category

    def global_metadata(self):
        cat = self.category
        tags = self.local_metadata.tags.copy()
        while cat:
            tags.union(cat.metadata.tags)
            cat = cat.parent
        return Metadata(tags=tags)

    @property
    def name(self) -> str:
        return self.path.stem

    def tags(self) -> set:
        return self.local_metadata.tags

    def remove_tag(self, tag: str) -> None:
        if tag in (tags:=self.local_metadata.tags):
            tags.remove(tag)
            self.write_metadata()

    def add_tag(self, tag: str) -> None:
        self.local_metadata.tags.add(tag)
        self.write_metadata()

    def write_metadata(self):
        d = self.local_metadata.to_json()
        with (self.path.parent / "metadata.json").open("w") as f:
            json.dump(d, f, indent=2)

    @abstractmethod
    def compile(self) -> int:...

    @staticmethod
    @abstractmethod
    def get_type() -> str:...

    def open(self):
        """
        Opens note as pdf
        """
        name = self.name
        pdf = f"{name}.pdf"
        if not (self.path / pdf).is_file():
            print(f"{pdf} not found, attempting to compile note {name}")
            self.compile()

        if not (self.path / pdf).is_file():
            print("Failed to compile")
            return

        open = open_cmd()
        subprocess.run([open, f"{self.path / pdf}"], stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL)


@dataclass
class TeXNote(Note):

    def compile(self) -> int:
        """
        Compiles .tex file into a pdf and returns the returncode
        """
        print(self.path / f"{self.path.name}.tex")
        result = subprocess.run(
            ['latexmk', "-pdf", str(self.path / f"{self.path.name}.tex")],
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            cwd = self.path
            )
        print(result.stderr)
        print(result.stdout)
        return result.returncode

    @staticmethod
    def get_type():
        return NoteType.LaTeX.value

    def __post_init__(self):
        if not Path.is_dir(self.path):
            raise ValueError(f"Directory {self.path} does not exist")


@dataclass
class TypNote(Note):


    def compile(self) -> int:
        """
        Compiles .tex file into a pdf and returns the returncode
        """
        result = subprocess.run(
            ['typst', "compile", "-f", "pdf", str(self.path / f"{self.path.name}.typ")],
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            cwd = self.path
            )
        return result.returncode

    @staticmethod
    def get_type():
        return NoteType.Typst.value

    def __post_init__(self):
        if not Path.is_dir(self.path):
            raise ValueError(f"Directory {self.path} does not exist")





class NotesManager:

    def __init__(self, root: Path):
        """
        root: directory at the root of notes
        """
        self.note_dir = root
        self.root_category = self._init_root_cat()
        self._generate_tree(self.root_category)

    def _init_root_cat(self) -> Category:
        meta = Metadata(set(self._load_from_json(self.note_dir/ "cat-metadata.json")["tags"]))
        root_cat = Category(meta, self.note_dir)
        return root_cat

    def _generate_tree(self, parent: Category):
        for dir in parent.path.iterdir():
            if not dir.is_dir():
                continue
            if (dir / "cat-metadata.json").is_file():
                d = self._load_from_json(dir / "cat-metadata.json")
                metadata = Metadata(d["tags"])
                cat = Category(metadata, dir, parent=parent)
                parent.children.append(cat)
                cat.parent = parent
                self._generate_tree(parent=cat)

            elif (meta_file := dir / "metadata.json").is_file():
                d = self._load_from_json(meta_file)
                localmetadata = Metadata(d["tags"])

                if any(file.suffix == ".typ" for file in dir.iterdir() if file.is_file()):
                    note = TypNote(dir,localmetadata, parent)
                    parent.notes.append(note)
                else:
                    note = TeXNote(dir,localmetadata, parent)
                    parent.notes.append(note)
        return


    @staticmethod
    def _load_from_json(path: Path) -> dict:
        #TODO this is god awful and needs to be rethought
        with open(path, "r") as f:
            metadata = json.load(f)
        if "tags" not in metadata:
            metadata["tags"] = set()
        return metadata

    def new_note(self, name: str, parent: Category, note_type: NoteType) -> None:
        """
        name: note name, stem of .tex file path (no suffix)
        """
        if name.upper() in set(note.name.upper() for note in parent.notes):
            print(f"Failed to create '{name}'. Its equal (up to capatilization) to existing note")
            return

        if name == "resources":
            raise ValueError("Failed to create note, the name 'resources' is resereved")

        # TODO clean this up. + fix cat-metadata vs metadata
        if note_type == NoteType.LaTeX:
            note_dir_path = parent.path / name
            note_path = note_dir_path / f"{name}.tex"
            metadata_path = note_dir_path / "metadata.json"

            note_dir_path.mkdir()
            note_path.touch()
            self._init_metadata(metadata_path)

            note = TeXNote(note_dir_path, Metadata(), parent)
            parent.notes.append(note)

        elif note_type == NoteType.Typst:
            note_dir_path = parent.path / name
            note_path = note_dir_path / f"{name}.typ"
            metadata_path = note_dir_path / "metadata.json"

            note_dir_path.mkdir()
            note_path.touch()
            self._init_metadata(metadata_path)

            note = TypNote(note_dir_path, Metadata(), parent)
            parent.notes.append(note)

#            note_template = Path(config["note-template"])
#            dest = dir / f"{note}.tex"
#            shutil.copy(note_template, dest)

#        with self.refs_file.open(mode="a") as f:
#            f.write(f"\\externaldocument[{note}-]{{../{note}/{note}}}\n")
#        new_note = Note(dir)
#        self.notes[new_note.name()] = new_note
#
#        if config["set-note-title"]:
#            self.insert_title(dir / f"{name}.tex", new_note.name())

    def new_category(self, name, parent=None):
        if parent is None:
            if not name in (cat.name for cat in self.root_category.children):
                cat = Category(Metadata(), self.note_dir / name)
                self.root_category.children.append(cat)
                cat.parent = self.root_category
            else:
                return
        else:
            if not name in (cat.name for cat in parent.children):
                cat = Category(Metadata(), self.note_dir / name)
                parent.children.append(cat)
                cat.parent = parent
            else:
                return

        cat.path.mkdir()
        self._init_metadata(cat.path / "cat-metadata.json")

    @staticmethod
    def _init_metadata(path: Path):
        with open(path, "w") as f:
            json.dump({}, f, indent=2)


    def rename(self, note: Note, new_name):
        pass

    def del_note(self, note: Note):
        dir = note.path
        shutil.rmtree(dir)

    def insert_title(self):
        pass

    def get_note(self, name: str, category: Category) -> Note | None:
        # Support filter by parent
        res = None
        for note in category.notes:
            if note.name == name:
                return note
        for child in category.children:
            res = self.get_note(name, child)
        return res



def serialize_category(cat: Category) -> dict:
    # Should probably be name: {}
    return {
            "name": cat.name,
            "path": str(cat.path.relative_to(ROOT_DIR).as_posix()), # this breaks if dir chagnes from MathNote
            "notes": [
                {
                    "name": note.name,
                    "type": note.get_type()
                }
                for note in cat.notes
                ],
            "children": [serialize_category(child) for child in cat.children]
            }
