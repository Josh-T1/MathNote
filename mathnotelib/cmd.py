from pathlib import Path
import logging
from typing import Protocol
import argparse
import sys
import json

from PyQt6.QtWidgets import QApplication

from .ui import (MainWindow, TabbedSvgViewer,NavBarContainer, SettingsNavBar, CourseNavBar, NotesNavBar,
                 FlashcardView, CourseController, LiveTypstController, NoteController, FlashcardController,
                 ViewContainer, FlashcardNavBar, ViewController)
from .config import Config
from .models import Course
from ._enums import FileType
from .services import NotesRepository, CourseRepository


CONFIG = Config()

logger = logging.getLogger("mathnote")


"""
This code is fucked and needs to be re-written
"""

def load_json(file: str):
    with open(file, "r") as f:
        contents = json.load(f)
    return contents


def dump_json(file: str, contents: str) -> None:
    with open(file, "w") as f:
        json.dump(contents, f)

class Command(Protocol):
    def cmd(self, namespace) -> None: ...


class NoteViewer(Command):
    def __init__(self, project_config: Config):
        self.config = project_config

    def cmd(self, namespace: argparse.Namespace) -> None:
        app = QApplication(sys.argv)

        notes_view = TabbedSvgViewer()
        flashcard_view = FlashcardView()
        view_container = ViewContainer(notes_view, flashcard_view)

        notes_navbar = NotesNavBar()
        courses_navbar = CourseNavBar()
        flashcards_navbar = FlashcardNavBar()
        settings_navbar = SettingsNavBar(CONFIG)
        navbar_container = NavBarContainer(notes_navbar, courses_navbar, flashcards_navbar, settings_navbar)

        window = MainWindow(navbar_container, view_container)

        notes_controller = NoteController(window, notes_navbar,notes_view)
        coures_controller = CourseController(window, courses_navbar, notes_view)
        preview_controller = LiveTypstController(window, notes_view)
        flashcard_controller = FlashcardController(window, flashcards_navbar, flashcard_view)
        view_controller = ViewController(navbar_container, view_container)

        flashcard_controller.run()
        window.resize(800, 600)
        window.show()
        sys.exit(app.exec())




class CourseCommand(Command):
    """ Class command """

    def __init__(self, project_config: Config):
        self.project_config = project_config
        self.course_repo = CourseRepository(self.project_config)

    def create_course(self, namespace: argparse.Namespace):
        logger.info(f"Creating course with name: {namespace.name[0]}")
        self.course_repo.create_course(namespace.name[0])
        if namespace.user_input is not None:
            self._get_user_input(self.course_repo.courses()[namespace.name[0]])

    def get_course_information(self, name: str):
        course = self.course_repo.courses().get(name, None)
        if course is None:
            print(f"Course {name} does not exist")
            return
        print(self.beautify_output(course.course_info))

    def handle_active(self) -> str | None:
        logger.debug("Finding active course")
        active = self.get_active()
        if isinstance(active, Course):
            active = active.name
            print(f"Active course: {active}")
        else:
            print("No active courses")

    def cmd(self, namespace: argparse.Namespace):
        if (course:= namespace.name[0]) is None:
            return

        if namespace.new_course:
            self.create_course(namespace)
            return

        if namespace.information:
            self.get_course_information(course)

        if namespace.open_main:
            self.open_main(course)

        if namespace.new_lecture:
            course_obj = self.course_repo.get_course(course)
            if course_obj is None:
                print(f"Failed to create new lecture, no course with name: {course}")
            else:
                self.course_repo.create_lecture(course_obj)

        # TODO determine file type
        if namespace.new_assignment:
            course_obj = self.course_repo.get_course(course)
            if course_obj is None:
                print(f"Failed to create new assignment, no course with name: {course}")
            else:
                self.course_repo.create_assignment(course_obj)

    def _get_user_input(self, course: Course):
        path = course.path / "course_info.json"
        dic = load_json(str(path))
        for key, val in dic.items():
            if val:
                continue

            if "time" in key:
                print("Input time in format HH:MM with leading zeros if necessary: ")
            elif "weekday" in key:
                print("Enter a list of comma seperated days for which the course occurs. e.g. Monday, Tuesday")
            elif "date" in key:
                print("Enter date in the format yyyy/mm/dd")
            res = input("$ ").strip()
            dic[key] = res
        dump_json(str(path), dic)

    @staticmethod
    def beautify_output(info: dict):
        """ convert dictionary into a more readable string """
        return '\n'.join([f"{k}: {v}" for k, v in info.items()])

    def open_main(self, name: str):
        print("TODO")
#        course = self.course_repo.get_course(name)
#        if course is None:
#            print(f"Could not find course: {name}")
#        else:
#            course.open_main()

    def get_active(self):
        return self.course_repo.get_active_course()


class NoteCommand(Command):
    """ Command for the creation, management, and visualization of notes """
    def __init__(self, project_config: Config):
        self.config = project_config
        self.note_dir = Path(project_config.root_path) / "Notes"
        self.notes_repo = NotesRepository(self.note_dir)

    def cmd(self, namespace: argparse.Namespace):


        if namespace.new_note:
            name, item_type, parent_path = namespace.new_note[0], namespace.note_type[0], namespace.parent[0]
            new_type = {"tex": FileType.LaTeX, "typ": FileType.Typst}.get(item_type)

            if parent_path is None:
                parent_cat = self.notes_repo.root_category
            else:
                print("TODO")
#                parent_cat = self.notes_repo.caate
#                if parent_cat is None:
#                    print(f"Invalid path for parent category {parent_path}")
#                    return

#            if new_type is None:
#                print(f"Invalid item type {item_type}")
#
#            else:
#                self.notes_repo.create_note(name, parent_cat, new_type)

#        elif namespace.new_category:
#            name, parent = namespace.new_category[0], namespace.parent[0]
#            if parent is None:
#                parent = self.notes_repo.root_category
#            else:
#                valid_parent = self.notes_repo.root_category.get_subcategory(parent)
#                if valid_parent is False:
#                    print(f"Invalid path for parent category {parent}")
#                    return
#            self.notes_repo.create_category(name, parent)

#        elif namespace.remove_note:
#            name, parent = namespace.remove_note[0], namespace.parent[0]
#            if parent is None:
#                parent = notes.root_category
#            else:
#                parent = notes.root_category.get_subcategory(parent)
#                if parent is None:
#                    print(f"Parent category {parent} does not exist")
#                    return
#
#            note = notes.get_note(name, parent)
#            if note is None:
#                print(f"Note {parent.path / name} does not exist")
#                return
#            try:
#                notes.del_note(note)
#            except Exception as e:
#                print(f"Failed to remove note {parent.path / name}")
#                print(e)

#        elif namespace.list_notes:
#            parent = namespace.parent[0]
#            if parent is None:
#                parent = notes.root_category
#            else:
#                parent = notes.root_category.get_subcategory(parent)
#                if parent is None:
#                    print(f"Parent category {namespace.parent[0]} does not exist")
#                    return

            # TODO re-work this
#            for note in parent.children:
#                if isinstance(note, Note):
#                    print(note.name)

#        elif namespace.open_note:
#            note = notes.get_note(namespace.open_note[0], notes.root_category)
#            if note is None:
#                print(f"Note {namespace.open_note[0]} does not exist")
#            else:
#                note.open()

#        elif namespace.compile_note:
#            parent = namespace.parent[0]
#            if parent is None:
#                parent = notes.root_category
#            else:
#                parent = notes.root_category.get_subcategory(Path(namespace.parent[0]))
#                if parent is None:
#                    print(f"Parent category {namespace.parent[0]} does not exist")
#                    return
#            note = notes.get_note(namespace.compile_note[0], parent)
#            if note is None:
#                print(f"Note {namespace.compile_note[0]} does not exist")
#            else:
#                note.compile()

        #TODO need parent category aswell
#        elif namespace.rename:
#            old_name, new_name, parent = namespace.rename[0], namespace.rename[1], namespace.parent[0]
#            if parent is None:
#                parent = notes.root_category
#            else:
#                parent = notes.root_category.get_subcategory(Path(namespace.parent[0]))
#                if parent is None:
#                    print(f"Parent category {namespace.parent[0]} does not exist")
#                    return
#            note = notes.get_note(old_name, parent)
#            if note is None:
#                print(f"Note {parent.path / old_name} does not exist")
#                return
#
#            try:
#                notes.rename(note, new_name)
#            except ValueError as e:
#                print(f"Note with name '{new_name}' already exists")

#
#        elif namespace.tag:
#            note = notes.get_note(namespace.tag[0])
#            if note is None:
#                print(f"Note {namespace.tag[0]} does not exist")
#            else:
#                note.add_tag(namespace.tag[1])
#
#        elif namespace.remove_tag:
#            note = notes.get_note(namespace.remove_tag[0])
#            if note is None:
#                print(f"Note {namespace.remove_tag[0]} does not exist")
#            else:
#                note.remove_tag(namespace.remove_tag[1])
#
#        elif namespace.exists:
#            note = notes.get_note(namespace.exists[0])
#            if note is None:
#                print("0")
#            else:
#                print("1")

#        elif namespace.plot_network:
#            from PyQt6.QtWidgets import QApplication
#            import sys
            # Consider the error when file has never been compiled
#            matrix = notes.build_adj_matrix()
#            app = QApplication(sys.argv)
#            window = MainWindow()
#            window.show()
#            sys.exit(app.exec())

