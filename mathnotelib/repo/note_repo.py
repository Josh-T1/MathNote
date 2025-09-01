from pathlib import Path
import json
import shutil
import logging
from datetime import datetime

from mathnotelib.models.source_file import Assignment, Lecture

from ..services import get_header_footer
from ..utils import Config, CONFIG, FileType
from ..models import Note, Category, Course, Metadata

logger = logging.getLogger(__name__) # TODO

class NotesRepository:
    _instances: dict[Path, 'NotesRepository'] = {}

    def __init__(self, root: Path):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.repo_root = root
        self.root_category = self.build_root_category()

    def __new__(cls, path: Path):
        if cls._instances.get(path) is None:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instances[path] = instance
        return cls._instances[path]

    def build_root_category(self) -> Category:
        metadata = self.load_metadata(self.repo_root / "cat-metadata.json")
        root_cat = Category(metadata, self.repo_root, [])
        notes = self._get_notes(root_cat)
        root_cat.notes = notes
        return root_cat

    def create_note(self, name: str, parent: Category, note_type: FileType) -> Note | None:
        """
        name: note name, stem of .tex/typ file path (no suffix)
        """
        if name.upper() in {note.name.upper() for note in parent.notes}:
            ValueError(f"Failed to create note '{name}'. It's equal (up to capatilization) to existing note")
        if not name:
            raise ValueError()
        if name.lower() == "resources":
            ValueError("Failed to create note, 'resources' is a reserved name")
        ext = "tex" if note_type == FileType.LaTeX else "typ"
        note_dir_path = parent.path / f"{name}.note"
        note_path = note_dir_path / f"{name}.{ext}"
        metadata_path = note_dir_path / "metadata.json"
        note_dir_path.mkdir()
        self._init_metadata(metadata_path)
        note_template = CONFIG.template_files[note_type]["note_template"]
        shutil.copy(note_template, note_path)
        new_note = Note(note_path, Metadata(set()), parent)
        parent.notes.append(new_note)
        if CONFIG.set_note_title:
            self.insert_title(new_note)
        return new_note

    # TODO make new_parent_cat an arg not kwarg
    def rename_note(self, note: Note, new_name: str, new_parent_cat: Category | None=None):
        old_cat, old_path = note.category, note.path
        old_dir = note.path.parent
        parent_cat = note.category if new_parent_cat is None else new_parent_cat
        if any(new_name.upper() == note.name.upper() for note in parent_cat.notes):
            raise ValueError()

        new_dir = parent_cat.path / f"{new_name}.note"
        new_path = note.path.parent / f"{new_name}{note.path.suffix}"
        if new_dir.exists() or new_path.exists():
            raise FileExistsError(f"Directory '{new_dir}' already exists")
        old_path.rename(new_path)
        old_dir.rename(new_dir)


    def delete_note(self, note: Note):
        # update parent category
        dir = note.path.parent
        shutil.rmtree(dir)
        note.category.notes.remove(note)

    # TODO
    def insert_title(self, note: Note):
        pass

#    def get_note(self, name: str, category: Category) -> Note | None:
#        # Support filter by parent
#        res = None
#        for note in category.notes:
#            if note.name == name:
#                return note
#        for child in category.children():
#            res = self.get_note(name, child)
#        return res

    def add_note_tag(self, note: Note, tag: str):
        note.add_tag(tag)
        self.write_metadata(note)

    def delete_note_tag(self, note: Note, tag: str):
        note.remove_tag(tag)
        self.write_metadata(note)

    def _get_notes(self, category: Category) -> list[Note]:
        notes = []
        for dir in category.path.iterdir():
            if not dir.is_dir():
                continue
            metadata_file = dir / "metadata.json"
            if not metadata_file.is_file():
                continue

            metadata = self.load_metadata(metadata_file)
            for file in dir.iterdir():
                if file.is_file() and file.suffix in {".typ", ".tex"}:
                    note = Note(file, metadata, category)
                    notes.append(note)
        return notes

    def add_category_tag(self, category: Category, tag: str):
        category.add_tag(tag)
        self.write_metadata(category)

    def delete_category_tag(self, category: Category, tag: str):
        category.remove_tag(tag)
        self.write_metadata(category)

    def delete_category(self, cat: Category):
        dir = cat.path
        shutil.rmtree(dir)

    # TODO: raise error
    def rename_cat(self, cat: Category, new_name: str, new_parent_cat: Category | None=None):
        old_parent = cat.parent
        if old_parent is None:
            return
        new_cat = new_parent_cat if new_parent_cat is not None else old_parent
        sub_categories = self.get_sub_categories(new_cat)
        if any(new_name.upper() == child.name.upper() for child in sub_categories):
            raise ValueError("") # TODO
        new_dir = new_cat.path / new_name
        if new_dir.exists():
            raise ValueError() # TODO
        cat.path.rename(new_dir)

    # creates directory
    def create_category(self, name: str, parent: Category) -> Category | None:
        if not name: # TODO
            raise ValueError()
        sub_categories = self.get_sub_categories(parent)
        if any(cat.name == name for cat in sub_categories):
            return
        dir = parent.path / name
        meta_path = dir / "cat-metadata.json"
        dir.mkdir()
        self._init_metadata(meta_path)
        metadata = Metadata(set())
        cat = Category(metadata, dir, [], parent=parent)
        return cat

    def get_sub_categories(self, category: Category) -> list[Category]:
        children: list[Category] = []
        for dir in category.path.iterdir():
            if not dir.is_dir():
                continue
            if (dir / "cat-metadata.json").is_file():
                metadata = self.load_metadata(dir / "cat-metadata.json")
                cat = Category(metadata, dir, [], parent=category)
                cat.notes = self._get_notes(cat)
                children.append(cat)
        return children

    @staticmethod
    def _init_metadata(path: Path):
        # TODO: currently we write empty dict...
        with open(path, "w") as f:
            json.dump({}, f, indent=2)

    def write_metadata(self, item: Note | Category):
        file_name = "metadata.json" if isinstance(item, Note) else "cat-metadata.json"
        d = item.metadata.to_dict()
        with (item.path / file_name).open("w") as f:
            json.dump(d, f, indent=2)

    def load_metadata(self, path: Path) -> Metadata:
        #TODO this is god awful and needs to be rethought
        with open(path, "r") as f:
            d = json.load(f)
        if "tags" not in d:
            d["tags"] = set()
        metadata = Metadata(d["tags"])
        return metadata

#    def _generate_tree(self, parent: Category):
#        for dir in parent.path.iterdir():
#            if not dir.is_dir():
#                continue
#            if (dir / "cat-metadata.json").is_file():
#                d = load_from_json(dir / "cat-metadata.json")
#                metadata = Metadata(d["tags"])
#                cat = Category(metadata, dir, parent=parent)
#                cat.parent = parent
#                self._generate_tree(parent=cat)
#        return
    # rename to create + build note object then append
