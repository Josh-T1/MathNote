from pathlib import Path
import json
import shutil
import logging

from ..config import CONFIG, Config
from ..models import Note, Category, Metadata
from .._enums import FileType
from ..exceptions import InvalidNameError, NoteExistsError, CategoryExistsError

logger = logging.getLogger(__name__) # TODO

class NotesRepository:
    """Singleton class (one class per root directory) representing the notes repository"""
    _instances: dict[Path, 'NotesRepository'] = {}

    def __init__(self, config: Config):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.config = config
        self.repo_root = config.root_path / "Notes"
        self.root_category = self.build_root_category()

    def __new__(cls, config: Config):
        path = config.root_path / "Notes"
        if cls._instances.get(path) is None:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instances[path] = instance
        return cls._instances[path]

    def __repr__(self) -> str:
        return f"<NotesRepository root={repr(self.repo_root)}>"

    def build_root_category(self) -> Category:
        """Loads and returns Category object representing root of notes repository"""
        metadata = self.load_metadata(self.repo_root / "cat-metadata.json")
        root_cat = Category(metadata, self.repo_root, [])
        notes = self._get_notes(root_cat)
        root_cat.notes = notes
        return root_cat

    def create_note(self, name: str, parent: Category, note_type: FileType) -> Note:
        """
        Args:
            name: name of new note, no suffix (i.e., test is valid test.tex is not)
            parent: category containing note
            note_type: file type of new note

        Returns:
            Note: if successfullyy created else None

        Raises:
            NoteExistsError: If a note already exists with the same name in parent category (up to capatilization)
            InvalidNameError: If protected name is used or name arg is left blank

        name: note name, stem of .tex/typ file path (no suffix)
        """
        name = name.replace(" ", "-")
        if name.upper() in {note.name.upper() for note in parent.notes}:
            raise NoteExistsError(f"Failed to create note '{name}'. It's equal (up to capatilization) to existing note")
        if not name:
            raise InvalidNameError("Name cannot be blank")
        if name.lower() == "resources":
            InvalidNameError("Failed to create note, 'resources' is a reserved name")

        note_dir_path = parent.path / f"{name}.note"
        note_path = note_dir_path / f"{name}{note_type.extension}"
        metadata_path = note_dir_path / "metadata.json"
        note_dir_path.mkdir()
        self._init_metadata(metadata_path)
        note_template = self.config.template_files[note_type]["note_template"]
        shutil.copy(note_template, note_path)
        new_note = Note(note_path, Metadata(set()), parent)
        parent.notes.append(new_note)

        if self.config.set_note_title:
            self.insert_title(new_note)
        return new_note

    # TODO make new_parent_cat an arg not kwarg
    def rename_note(self, note: Note, new_name: str, new_parent_cat: Category | None=None) -> Note:
        """Rename note

        Args:
            note: note object to be renamed
            new_name: rename note to new_name, name should not include suffix
            new_parent_cat: If specified the note will not only be renamed but also moved from its current
                            parent category to the new parent category

        Raises:
            NoteExistsError: raised if a note under new_parent_cat with name new_name (up to capatilization) already exists
        """
        # check to ensure old != new
        old_cat, old_dir = note.category, note.path.parent
        old_cat.notes.remove(note)
        parent_cat = old_cat if new_parent_cat is None else new_parent_cat
        target_dir = parent_cat.path / f"{new_name}.note"

        moved_path_ = target_dir /f"{note.name}{note.path.suffix}"


        if any(new_name.upper() == note.name.upper() for note in parent_cat.notes) or target_dir.exists():
            raise NoteExistsError(
                    f"Renaming {note.name} to {new_name} failed.\nA note with the same name (up to capatilization) already exists under the category {parent_cat.name}"
                    )

        new_dir = old_dir.rename(target_dir)
        new_path_ = new_dir / f"{new_name}{note.path.suffix}"
        new_path = moved_path_.rename(new_path_)
        new_note = Note(new_path, note.metadata, parent_cat)
        parent_cat.notes.append(new_note)
        return new_note


    def delete_note(self, note: Note):
        dir = note.path.parent
        shutil.rmtree(dir)
        note.category.notes.remove(note)

    # TODO
    def insert_title(self, note: Note):
        """Inserts auto generated title into note source file"""
        pass

    def add_note_tag(self, note: Note, tag: str):
        note.add_tag(tag)
        self.write_metadata(note)

    def delete_note_tag(self, note: Note, tag: str):
        note.remove_tag(tag)
        self.write_metadata(note)

    def _get_notes(self, category: Category) -> list[Note]:
        """Returns all notes directly under a given category (not recursive)"""
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

    def rename_cat(self, cat: Category, new_name: str, new_parent_cat: Category | None=None) -> Category:
        """Rename category

        Args:
            cat: category to be renamed
            new_name: obvious
            new_parent_cat: If specified the category will be renamed and moved to be under new_parent_cat

        Raises:
            InvalidNameError: If new name is blank, or new name is equal to existing category under
                                new_parent_cat (up to capatilization)
            ValueError: If category to be renamed is the root notes repository category
        """
        old_parent = cat.parent
        if not new_name:
            raise InvalidNameError("New name cannot be left blank")
        if old_parent is None:
            raise ValueError("Root category cannot be renamed")

        parent = new_parent_cat if new_parent_cat is not None else old_parent
        sub_categories = self.get_sub_categories(parent)
        new_dir = parent.path / new_name
        if any(new_name.upper() == child.name.upper() for child in sub_categories) or new_dir.exists():
            raise CategoryExistsError(f"Category with name '{new_name}' already exists under category {parent}")

        new_cat_path = cat.path.rename(new_dir)
        new_cat = Category(cat.metadata, new_cat_path, cat.notes, parent)
        return new_cat

    def create_category(self, name: str, parent: Category) -> Category:
        """Creates new category

        Args:
            name: name for new category
            parent: parent for new category. For top level categories set parent=root_category which generated on initialization

        Raises:
            CategoryExistsError: If category already exists with the same name (up to capatilization)

        Returns:
            new category
        """
        name = name.replace(" ", "-")
        if not name:
            raise InvalidNameError("Name cannot be left blank")
        sub_categories = self.get_sub_categories(parent)
        if any(cat.name == name for cat in sub_categories):
            CategoryExistsError(
                    f"Failed to create category '{name}'. It's equal (up to capatilization) to an existing category"
                    )
        dir = parent.path / name
        meta_path = dir / "cat-metadata.json"
        dir.mkdir()
        self._init_metadata(meta_path)
        metadata = Metadata(set())
        cat = Category(metadata, dir, [], parent=parent)
        return cat

    def get_sub_categories(self, category: Category) -> list[Category]:
        """Gets all subcategories under category (non recursive)"""
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
        """Initializes metadata json file with emtpy dict"""
        # TODO: currently we write empty dict...
        with open(path, "w") as f:
            json.dump({}, f, indent=2)

    def write_metadata(self, item: Note | Category):
        """Saves items metadata to associated json file"""
        file_name = "metadata.json" if isinstance(item, Note) else "cat-metadata.json"
        d = item.metadata.to_dict()
        with (item.path / file_name).open("w") as f:
            json.dump(d, f, indent=2)

    def load_metadata(self, path: Path) -> Metadata:
        """Loads and returns Metadata object from json file data associated to path"""
        with open(path, "r") as f:
            d = json.load(f)
        if "tags" not in d:
            d["tags"] = set()
        metadata = Metadata(d["tags"])
        return metadata

    def reload_category(self, category: Category):
        notes = self._get_notes(category)
        category.notes = notes

    @staticmethod
    def note_to_path(note: Note) -> list[str]:
        parent, name = note.category, note.name
        path = [name]
        while parent is not None:
            path.append(parent.name)
            parent = parent.parent
        path.reverse()
        return path

    @staticmethod
    def category_to_path(cat: Category) -> list[str]:
        parent, name = cat.parent, cat.name
        path = [name]
        while parent is not None:
            path.append(parent.name)
            parent = parent.parent
        path.reverse()
        return path


    def path_to_category(self, path: list[str]) -> Category:
        if len(path) < 2:
            raise ValueError("Invalid path, must contain parent category name and target category name")

        *category_names, target_cat_name = path
        parent = self.root_category
        if parent.name != category_names[0]:
            raise ValueError(f"Invalid root element in path: {path}")
        for cat_name in category_names[1:]:
            subcategories = self.get_sub_categories(parent)
            for cat in subcategories:
                if cat.name == cat_name:
                    parent = cat
                    break
            else:
                raise ValueError(f"Could not determine Category from path: {path}")
        for cat in self.get_sub_categories(parent):
            if cat.name == target_cat_name:
                return cat

        raise ValueError(f"Could not determine Category from path: {path}")


    def path_to_note(self, path: list[str]) -> Note:
        if len(path) < 2:
            raise ValueError("Invalid path, must contain root category name and note name")

        *category_names, note_name = path
        parent = self.root_category
        if parent.name != category_names[0]:
            raise ValueError(f"Invalid root element in path: {path}")
        for cat_name in category_names[1:]:
            subcategories = self.get_sub_categories(parent)
            for cat in subcategories:
                if cat.name == cat_name:
                    parent = cat
                    break
            else:
                raise ValueError(f"Could not determine Note from path: {path}")
        for note in parent.notes:
            if note.name == note_name:
                return note

        raise ValueError(f"Could not determine Note from path: {path}")


        # check this works on every iteration ++ check that note actually exsts under paretn






