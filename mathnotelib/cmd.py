from pathlib import Path
import logging
from typing import Callable, Protocol
import argparse
import sys
import json

from PyQt6.QtWidgets import QApplication

from .ui import (MainWindow, TabbedSvgViewer,NavbarContainer, SettingsNavbar, CourseNavbar, NotesNavbar,
                 FlashcardView, CourseController, LiveTypstController, NoteController, FlashcardController,
                 ViewContainer, FlashcardNavbar, ViewController, SettingsController)
from .config import CONFIG
from .models import Course
from .enums import FileType
from .services import NotesRepository, CourseRepository


logger = logging.getLogger(__name__)


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
    def cmd(self, namespace: argparse.Namespace) -> None: ...


class NoteViewer(Command):
    def cmd(self, namespace: argparse.Namespace) -> None:
        app = QApplication(sys.argv)

        notes_view = TabbedSvgViewer()
        flashcard_view = FlashcardView()
        view_container = ViewContainer(notes_view, flashcard_view)

        notes_navbar = NotesNavbar()
        courses_navbar = CourseNavbar()
        flashcards_navbar = FlashcardNavbar()
        settings_navbar = SettingsNavbar(CONFIG)
        navbar_container = NavbarContainer(notes_navbar, courses_navbar, flashcards_navbar, settings_navbar)

        window = MainWindow(navbar_container, view_container)

        notes_controller = NoteController(window, notes_navbar,notes_view)
        coures_controller = CourseController(window, courses_navbar, notes_view)
        preview_controller = LiveTypstController(window, notes_view)
        flashcard_controller = FlashcardController(window, flashcards_navbar, flashcard_view)
        view_controller = ViewController(window, navbar_container, view_container)
        settings_controller = SettingsController(window, settings_navbar)
        window.set_close_callback(flashcard_controller.stop)
        window.show()
        sys.exit(app.exec())




class CourseCommand(Command):
    """ Class command """

    def __init__(self):
        self.course_repo = CourseRepository(CONFIG)

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
