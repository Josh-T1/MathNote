from pathlib import Path
import json
import shutil
import subprocess
from mathnotelib.utils import open_cmd


class Note:
    """
    Represents a latex note and its corresponding metadata, e.g tags, aux files

    """

    def __init__(self, source: Path):
        """
        source: note directory
        """
        if not source.is_dir():
            raise ValueError("Must initialize note with valid directory path or call Note.create")
        self.path = source
        self._tags = None
        self._metadata = None

    def name(self):
        return self.path.stem

    @property
    def metadata(self):
        if self.metadata is None:
            with open(self.path / "metadata.json", "r") as f:
                self._metadata = json.load(f)

    @property
    def tags(self) -> set:
        if self._tags is None:
            if self._metadata is None:
                self.metadata
            self._tags = set(self._metadata["tags"]) # type: ignore
        return self._tags

    def add_tag(self, tag: str):
        self.tags.update(tag)
        self.update_metadata()

    def compile(self) -> int:
        tex = self.path / f"{self.name()}.tex"
        result = subprocess.run(
            ['latexmk', '-f', '-pdflatex="pdflatex -interaction=nonstopmode"', str(tex)],
            stdout = subprocess.DEVNULL,
            stderr = subprocess.DEVNULL,
            )
        return result.returncode

    def remove_tag(self, tag: str):
        if tag in self.tags:
            self.tags.remove(tag)
            self.update_metadata()

    def update_metadata(self):
        if self._metadata is None:
            return
        if not self._tags is None:
            self._metadata["tags"] = list(self._tags)
        with (self.path / "metadata.json").open("w") as f:
            json.dump(self._metadata, f, indent=4)

    def open(self):
        name = self.name()
        pdf = f"{name}.pdf"
        if not (self.path / pdf).is_file():
            self.compile()
        open = open_cmd()
        subprocess.run([open, f"{self.path / pdf}"], stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL)

    def __repr__(self):
        return f"Note( {self.path} )"

    def __str__(self):
        return f"{self.name}"


class NotesManager:
    """
    Container for Note objects. Its assumed the note directory has been properly inizialized, e.i the following
    directory structure exists:

    note/resources/
                  |-refs.tex
                  |-macros.tex
                  |-preamble.tex

    """
    def __init__(self, root: Path):
        self.note_dir = root
        self.resources_dir = self.note_dir / "resources"
        self.refs_file = self.resources_dir / "refs.tex"
        self.macros = self.resources_dir / "macros.tex"
        self.preamble = self.resources_dir / "preamble.tex"

        if (not self.refs_file.is_file() or not self.macros.is_file() or not self.preamble.is_file()):
            raise ValueError("Note directory has not been initialized correctly\nMissing one of: macros.tex, preamble.tex, refs.tex")

        self._notes = None

    @property
    def notes(self) -> dict[str, Note]:
        if self._notes is None:
            self._notes = {
                    note.name: Note(note)
                    for note in self.note_dir.iterdir()
                    if note.is_dir() and note.name != "refs"
                    }
        return self._notes


    def is_note(self, stem: str) -> bool:
        """ Takes in formated stem of filepath, e.g NewNote when creating new_note.tex """
        return (self.note_dir / stem).is_dir()

    def new_note(self, note: Path) -> None:
        if note.is_dir():
            print(f"Note {note} already exists")
            return

        dir = self.note_dir / note
        dir.mkdir()
        dest = dir / f"{note}.tex"
        shutil.copy(self.resources_dir / "refs.tex", dest)

        with self.refs_file.open(mode="a") as f:
            f.write(f"\\externaldocument[]{{../note/{note}}}")
        new_note = Note(dir)
        self.notes[new_note.name()] = new_note

    def list_notes(self):
        for note in self.notes:
            print(str(note))

    def validate_name(self, name: str) -> bool:
        if "." in name or " " in name:
            return False
        return True

    def rename(self, name: str, new_name: str):
        note = self.notes.get(name, None)
        if not self.validate_name(new_name):
            print(f"Invalid name '{new_name}'")
            return
        if note is None:
            print(f"Note {name} does not exist")
            return
        if (self.note_dir / new_name).is_dir():
            print("Note {new_name} already exists")
            return
        shutil.move(note.path, self.note_dir / new_name)
        self.del_note(note.name())

    def del_note(self, name: str):
        note = self.notes.get(name, None)
        if note is None:
            print(f"Note {name} does not exist")
            return
        if note.path.exists() and note.path.is_dir():
            shutil.rmtree(note.path)
        del self.notes[name]
        del note

    def get_note(self, name: str) -> Note | None:
        return self.notes.get(name, None)
