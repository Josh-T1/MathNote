from pathlib import Path
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Optional

from .source_file import SourceFile, FileType, open_cmd
from ..utils import CONFIG

ROOT_DIR = Path(CONFIG.root_path)

def load_from_json(path: Path) -> dict:
    #TODO this is god awful and needs to be rethought
    with open(path, "r") as f:
        metadata = json.load(f)
    if "tags" not in metadata:
        metadata["tags"] = set()
    return metadata

@dataclass
class Metadata:
    tags: set = field(default_factory=set)

    def to_json(self):
        return {"tags": list[self.tags]}


class Category:
    """
    Acts as node with child Categories and notes
    """
    def __init__(self, metadata: Metadata, path: Path, children: Optional[list['Category']]  = None, parent: Optional['Category'] = None):
        self.metadata = metadata
        self.path = path
        self._children: Optional[list['Category']] = children
        self._notes: Optional[list[Note]] = None
        self.parent: Optional['Category'] = parent

    def notes(self, force: bool = False) -> list['Note']:
        """
        force: If true notes will be generated from files even if this instance has a cached list of categories
        """
        if not force and self._notes:
            return self._notes

        notes = []
        for dir in self.path.iterdir():
            if not dir.is_dir():
                continue
            if (meta_file := dir / "metadata.json").is_file():
                d = load_from_json(meta_file)
                localmetadata = Metadata(d["tags"])

                for file in dir.iterdir():
                    if file.is_file() and file.suffix in {".typ", ".tex"}:
                        note = Note(file, localmetadata, self)
                        notes.append(note)
        self._notes = notes
        return self._notes

    def children(self, force: bool = False) -> list['Category']:
        """
        force: If true children will be generated from files even if this instance has a cached list of categories
        """
        if not force and self._children:
            return self._children

        children = []
        for dir in self.path.iterdir():
            if not dir.is_dir():
                continue
            if (dir / "cat-metadata.json").is_file():
                d = load_from_json(dir / "cat-metadata.json")
                metadata = Metadata(d["tags"])
                cat = Category(metadata, dir, parent=self)
                children.append(cat)
                cat.parent = self
        self._children = children
        return self._children

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
        for child in self.children():
            if child.path.resolve() == path.resolve():
                return child
            else:
                res = child.get_subcategory(path)
        return res

@dataclass
class Note(SourceFile):
    """ TODO """
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

    def open(self):
        """
        Opens note as pdf
        """
        pdf_path = self.path.with_suffix(".pdf")
        if not pdf_path.is_file():
            print(f"{pdf_path} not found, attempting to compile note {self.path.stem}")
            # TODO
#            self.compile()
        # remove this-use return code
        if not pdf_path.is_file():
            print("Failed to compile")
            return

        open = open_cmd()
        subprocess.run([open, pdf_path], stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL, cwd=self.path.parent)


""" TODO: unfinished """
class NotesManager:
    def __init__(self, root: Path):
        """
        root: directory at the root of notes
        """
        self.note_dir = root
        self.root_category: Category = self._init_root_cat()
        self.children: list['Category'] = []
        self.notes: list['Note'] = []
        self._generate_tree(self.root_category)

    @classmethod
    def build_root_category(cls, root: Path) -> Category:
        meta = Metadata(
                set(load_from_json(root / "cat-metadata.json")["tags"])
                )
        root_cat = Category(meta, root)
        return root_cat

    def _init_root_cat(self) -> Category:
        meta = Metadata(set(load_from_json(self.note_dir/ "cat-metadata.json")["tags"]))
        root_cat = Category(meta, self.note_dir)
        return root_cat

    def _generate_tree(self, parent: Category):
        for dir in parent.path.iterdir():
            if not dir.is_dir():
                continue
            if (dir / "cat-metadata.json").is_file():
                d = load_from_json(dir / "cat-metadata.json")
                metadata = Metadata(d["tags"])
                cat = Category(metadata, dir, parent=parent)
                cat.parent = parent
                self._generate_tree(parent=cat)
        return

    def new_note(self, name: str, parent: Category, note_type: FileType) -> Note | None:
        """
        name: note name, stem of .tex/typ file path (no suffix)
        """
        if name.upper() in {note.name.upper() for note in parent.notes()}:
            print(f"Failed to create note '{name}'. It's equal (up to capatilization) to existing note")
            return

        if name == "resources":
            print(f"Failed to create note, the name 'resources' is resereved")
            return

        ext = "tex" if note_type == FileType.LaTeX else "typ"
        note_dir_path = parent.path / name
        note_path = note_dir_path / f"{name}.{ext}"
        metadata_path = note_dir_path / "metadata.json"
        note_dir_path.mkdir()
        self._init_metadata(metadata_path)
        note_template = CONFIG.template_files[note_type]["note_template"]
        shutil.copy(note_template, note_path)
        notes = parent.notes(force=True) # reload category notes
        # I dont like this
        for note in notes:
            if note.name == name:
                if CONFIG.set_note_title:
                    self.insert_title(note)
                return note
        return None

        # TODO support references?
        # TODO support auto generated titles
#            with self.refs_file.open(mode="a") as f:
#                f.write(f"\\externaldocument[{note}-]{{../{note}/{note}}}\n")
#            new_note = Note(dir)
#            note_template = Path(config["note-template"])
#            dest = dir / f"{note}.tex"
#            shutil.copy(note_template, dest)

#        with self.refs_file.open(mode="a") as f:
#            f.write(f"\\externaldocument[{note}-]{{../{note}/{note}}}\n")
#        new_note = Note(dir)
#        self.notes[new_note.name()] = new_note
    def del_category(self, cat: Category):
        parent = cat.parent
        # remove cat from parent cat if possible
        dir = cat.path
        shutil.rmtree(dir)
        if parent is not None:
            parent.children(force=True)


    def new_category(self, name, parent: Category | None=None) -> Category | None:
        head = self.root_category if parent is None else parent
        if not name in (cat.name for cat in head.children()):
            new_cat_path = head.path / name
            new_cat_path.mkdir()
            self._init_metadata(new_cat_path / "cat-metadata.json")
            head.children(force=True) # re-fresh category children
            for cat in head.children():
                if cat.name == name:
                    return cat
        return None

    @staticmethod
    def _init_metadata(path: Path):
        # TODO: currently we write empty dict...
        with open(path, "w") as f:
            json.dump({}, f, indent=2)

    def rename_cat(self, cat: Category, new_name: str, new_parent_cat: Category | None=None):
        # reload parent cat
        old_parent = cat.parent
        if old_parent is None:
            # TODO error msg? users can not rename Notes/
            return
        new_cat = new_parent_cat if new_parent_cat is not None else old_parent
        if any(new_name.upper() == child.name.upper() for child in new_cat.children()):
            raise
        new_dir = new_cat.path / new_name
        if new_dir.exists():
            raise FileExistsError()
        cat.path.rename(new_dir)

        old_parent.children(force=True)
        if new_cat.path != old_parent.path:
            new_cat.children(force=True)

    def rename_note(self, note: Note, new_name: str, new_parent_cat: Category | None=None):
        old_cat, old_path = note.category, note.path
        old_dir = note.path.parent
        parent_cat = note.category if new_parent_cat is None else new_parent_cat
        if any(new_name.upper() == note.name.upper() for note in parent_cat.notes()):
            return 1

        new_dir = parent_cat.path / new_name
        new_path = note.path.parent / f"{new_name}{note.path.suffix}"
        if new_dir.exists() or new_path.exists():
            raise FileExistsError(f"Directory '{new_dir}' already exists")
        old_path.rename(new_path)
        old_dir.rename(new_dir)

        old_cat.notes(force=True)
        if old_cat.path != parent_cat.path:
            parent_cat.notes(force=True)

    def del_note(self, note: Note):
        dir = note.path.parent
        shutil.rmtree(dir)
        note.category.notes(force=True)

    def insert_title(self, note: Note):
        pass

    def get_note(self, name: str, category: Category) -> Note | None:
        # Support filter by parent
        res = None
        for note in category.notes():
            if note.name == name:
                return note
        for child in category.children():
            res = self.get_note(name, child)
        return res
