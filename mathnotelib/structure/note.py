from pathlib import Path
import json
import shutil
import subprocess
from mathnotelib.utils import open_cmd, config
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from ..utils import NoteType
from enum import Enum
from .source_file import OutputFormat

ROOT_DIR = Path(config['root'])

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
    Category continaing a 'Tree' of child notes and child categories
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

                if any(file.suffix == ".typ" for file in dir.iterdir() if file.is_file()):
                    note = TypNote(dir,localmetadata, self)
                    notes.append(note)
                else:
                    note = TeXNote(dir,localmetadata, self)
                    notes.append(note)
        return notes

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

        return children


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
    def compile(self,
                output_format: OutputFormat = OutputFormat.PDF,
                output_dir: Optional[Path] = None,
                output_filename: Optional[str] = None,
                multi_page: bool = False,
                ) -> int:...

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

    def compile(self,
                output_format: OutputFormat = OutputFormat.PDF,
                output_dir: Optional[Path] = None,
                output_filename: Optional[str] = None,
                multi_page: bool = False
                ) -> int:
        """
        TODO: Test
        TODO: multi page appears to work but idk...

        output_format: Target output type
        output_dir: Should be where compilation occurs, however TypNote implements a workaround by compiling in self.path then
                    moving the files to output_dir / output_filename(self.path/self.name .ext). Typst compile does not have output dir flag
        output_filename: Set to specify output file name. Defaults to {self.name}.{ext}
        multi_page: If set to True, pages will be compiled with names {output_filename(self.name)}-{#}.ext

        returns: return code of final compilation command
        """
        filepath = str(self.path / self.path.name) + ".tex"
        cmd = ["pdflatex", "-interaction=nonstopmode"]
        if output_dir:
            cmd.append(f"-output-dir={output_dir}")
        if output_format == OutputFormat.PDF and output_filename: #Untested
            cmd.append(f"-jobname={output_filename}")
        cmd.append(filepath)
        result = subprocess.run(
            cmd,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            cwd = self.path
            )
        if output_format == OutputFormat.PDF or result.returncode !=0:
            return result.returncode

        if output_dir:
            pdf_path = (output_dir / self.path.name).with_suffix(".pdf")
        else:
            pdf_path = (self.path / self.path.name).with_suffix(".pdf")
        cmd_2 = ["pdf2svg", str(pdf_path)]

        if output_filename:
            cmd_2.append(str(pdf_path.with_name(output_filename)))
        else:
            cmd_2.append(str(pdf_path.with_suffix(".svg")))

        cwd = self.path if not output_dir else output_dir

        result_2 = subprocess.run(
              cmd_2,
              stdout=subprocess.DEVNULL,
              stderr=subprocess.DEVNULL,
              cwd=cwd
                )
        return result_2.returncode

    @staticmethod
    def get_type():
        return NoteType.LaTeX.value

    def __post_init__(self):
        if not Path.is_dir(self.path):
            raise ValueError(f"Directory {self.path} does not exist")


@dataclass
class TypNote(Note):

    #add format option
    #add clean resources
    def compile(self,
                output_format: OutputFormat = OutputFormat.PDF,
                output_dir: Optional[Path] = None,
                output_filename: Optional[str] = None,
                multi_page: bool = False
                ) -> int:
        """
        TODO: Has not been properly tested

        output_format: Target output type
        output_dir: Should be where compilation occurs, however TypNote implements a workaround by compiling in self.path then
                    moving the files to output_dir / output_filename(self.path/self.name .ext). Typst compile does not have output dir flag
        output_filename: Set to specify output file name. Defaults to {self.name}.{ext}
        multi_page: If set to True, pages will be compiled with names {output_filename(self.name)}-{#}.ext

        returns: return code of final compilation command
        """
        # Set default output_filename if not specified
        output_filename = output_filename if output_filename is not None else self.name + ".svg"
        # Set pattern for output_filename if there are multipile pages
        if multi_page and output_filename:
            output_filename = output_filename.replace(".svg", "") + "-{p}.svg"
        elif multi_page and output_filename is None:
            output_filename = self.name + "-{p}.svg"

        # Build compilation cmd
        filepath = str(self.path / self.path.name) + ".typ"
        cmd = ["typst", "compile", "--format"]
        cmd.append(output_format.value)
        cmd.append(filepath)

        if multi_page and output_filename: # verbose, lsp is dumb
            cmd.append(output_filename)

        result = subprocess.run(
            cmd,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            cwd = self.path
            )
        if result.returncode != 0:
            return 1

        # Move files as a workaround for lack of output directory flag
        if output_dir:
            if multi_page and output_filename: # verbose, lsp is dumb
                files = sorted(self.path.glob(f"{output_filename.split("-")[0]}*.svg"))
            else:
                files = [filepath.replace(".typ", ".svg")]
            partial_out_name = output_filename.split(".")[0]
            for i, file in enumerate(files, start=1):
                try:

                    shutil.move(file, output_dir / f"{partial_out_name}-{i}.svg")
                except Exception as e:
                    return 1
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
        self.root_category: Category = self._init_root_cat()
        self.children: list['Category'] = []
        self.notes: list['Note'] = []
        self._generate_tree(self.root_category)

    @classmethod
    def build_root_category(cls, root: Path) -> Category:
        meta = Metadata(set(load_from_json(root / "cat-metadata.json")["tags"]))
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

    def new_note(self, name: str, parent: Category, note_type: NoteType) -> None:
        """
        name: note name, stem of .tex/typ file path (no suffix)
        """
        if name.upper() in set(note.name.upper() for note in parent.notes()):
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
            self._init_metadata(metadata_path)

            note_template = Path(config["note-template"])
            dest = note_dir_path / f"{name}.tex"
            shutil.copy(note_template, dest)
            # TODO support references?
#            with self.refs_file.open(mode="a") as f:
#                f.write(f"\\externaldocument[{note}-]{{../{note}/{note}}}\n")
#            new_note = Note(dir)

            # TODO support auto generated titles
#            if config["set-note-title"]:
#                self.insert_title(dir / f"{name}.tex", new_note.name())

            parent.notes(force=True) # reload category notes



        elif note_type == NoteType.Typst:
            note_dir_path = parent.path / name
            note_path = note_dir_path / f"{name}.typ"
            metadata_path = note_dir_path / "metadata.json"

            note_dir_path.mkdir()
            note_path.touch()
            self._init_metadata(metadata_path)
            parent.notes(force=True) # reload category with notes

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
        #raise NotImplemented("This does not currently work")
        # we actually have to build directory and ensure it does not already exist
        head: Category = self.root_category if parent is None else parent
        if not name in (cat.name for cat in head.children()):
            new_cat_path = head.path / name
            new_cat_path.mkdir()
            self._init_metadata(new_cat_path / "cat-metadata.json")
            head.children(force=True) # re-fresh category children

    @staticmethod
    def _init_metadata(path: Path):
        with open(path, "w") as f:
            json.dump({}, f, indent=2)


    def rename(self, note: Note, new_name):
        # TODO
        pass

    def del_note(self, note: Note):
        dir = note.path
        shutil.rmtree(dir)

    def insert_title(self):
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
