from pathlib import Path
import subprocess
from .course.courses import Courses, Course
import logging
import os
from typing import Union, Protocol
from .global_utils import load_json, dump_json

logger = logging.getLogger("course")

class Command(Protocol):
    def cmd(self, namespace) -> None: ...

class FlashcardCommand(Command):
    """ Command for generating flashcards from latex files """
    _app = None
    _window = None
    _model = None
    _compilation_manager = None
    _controller = None
    _config = None

    def __init__(self, project_config: dict):
        self.config = project_config
        self._ensure_import()
        self._has_dependecies()


    @staticmethod
    def _has_dependecies():
        dependencies = [
                (None, "latexmk"),
                (None, "tlmgr"),
                ("tlmgr","preview"),
                ]
        failed = set()
        for package_manager, dependency in dependencies:
            try:
                if package_manager is None:
                    subprocess.run([dependency, "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.run([package_manager, dependency, "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except FileNotFoundError:
                failed.add(dependency)
                print(f"Missing dependency: {dependency}")
        if len(failed) != 0:
            exit()

    @classmethod
    def _ensure_import(cls):
        if cls._app is None or cls._window is None or cls._model is None or cls._compilation_manager is None or cls._controller is None:
            from PyQt6.QtWidgets import QApplication
            from .gui.window import MainWindow
            from .flashcard.flashcard_model import FlashcardModel, TexCompilationManager
            from .flashcard.flashcard_controller import FlashcardController
            cls._app = QApplication([])
            cls._window = MainWindow
            cls._model = FlashcardModel
            cls._compilation_manager = TexCompilationManager
            cls._controller = FlashcardController

    def cmd(self, namespace):
        compilation_manager = self._compilation_manager() #type: ignore - self._ensure_import is always called first
        flashcard_model = self._model(compilation_manager) #type: ignore - self._ensure_import is always called first
        window = self._window() #type: ignore
        controller = self._controller(window, flashcard_model, self.config) #type: ignore
        if (file := self.build_file(namespace)) is not None:
            controller.create_flashcards_from_file(file)
#            controller.create_flashcards_from_file(file, 'All')
        window.setCloseCallback(controller.close)
        controller.run(self._app)
        if not flashcard_model.compile_thread.stopped(): # Cant remember if I actually need this
            flashcard_model.compile_thread.wait_for_stop()

    def build_file(self, namespace) -> None | Path:
        if namespace.file is None:
            return None
        file = Path(namespace.file[0])
        if file.is_file():
            return file

        if namespace.dir is not None:
            full_path = Path(namespace.dir[0]) / file
            if full_path.is_file():
                return full_path

        return None

class ClassCommand(Command):
    """ Class command """
    def __init__(self, project_config):
        self.project_config = project_config
        self.courses_obj = Courses(self.project_config)

    def create_course(self, namespace):
        logger.info(f"Creating class with name: {namespace.name}")
        self.courses_obj.create_course(namespace.name)
        if namespace.user_input is not None:
            self._get_user_input(self.courses_obj.courses[namespace.name])

    def get_course_information(self, arg: str):
        if arg == 'all':
            info = [course.course_info for course in self.courses_obj.courses.values()]
        elif arg == 'recent':
            info = [list(self.courses_obj.courses.values())[-1].course_info]
        else:
            info = self.courses_obj.courses.get(arg, None)
            info = None if info is None else [info.course_info]

        if info is None:
            print(f"There is no information given arguments: {arg}")
            return
        for dic in info:
            print(self.buitify_output(dic))
            print("="*20)

    def handle_active(self) -> str | None:
        logger.debug("Finding active class")
        active = self.get_active()
        if isinstance(active, Course):
            active = active.name
            print(f"Active course: {active}")
        else:
            print("No active courses")

    def cmd(self, namespace):
        if (course:= namespace.name) is None:
            if namespace.information:
                print("Warning no class name was provided. Ignoring all flags besides '-i'")
                self.get_course_information(namespace)
            print("Must specify a class name")
            return

        if namespace.new_course:
            self.create_course(namespace)
            return

        if namespace.current_course:
            self.handle_active()

        if namespace.information:
            self.get_course_information(namespace)

        if namespace.open_main:
            self.open_main(course)

        if namespace.new_lecture:
            course_obj = self.courses_obj.get_course(course)
            if course_obj is None:
                print(f"Failed to create new lecture, no course with name: {course}")
            else:
                course_obj.new_lecture()

        if namespace.new_assignment:
            course_obj = self.courses_obj.get_course(course)
            if course_obj is None:
                print(f"Failed to create new assignment, no course with name: {course}")
            else:
                course_obj.new_assignment()
        else:
            print(f"Invalid arguments passed {namespace}")

    def _get_user_input(self, course: Course):
        path = course.path / "course_info.json"
        dic = load_json(str(path))
        for key, val in dic.items():
            if val:
                continue

            print(f"Input value for key: {key}")
            self._additional_message(key)
            res = input("$ ").strip()
#            self._validate_user_input(res)
            dic[key] = res
        dump_json(str(path), dic)

    @staticmethod
    def buitify_output(info: dict):
        """ convert dictionary into a more readable string """
        return '\n'.join([f"{k}: {v}" for k, v in info.items()])

    @staticmethod
    def _additional_message(key):
        if "time" in key:
            print("Input time in format HH:MM (24 hour clock format) with leading zeros")

        elif "weekday" in key:
            print("Enter a list of comma seperated days for which the course occurs. ie Monday, Tuesday")
        elif "date" in key:
            print("Enter date in the format yyyy/mm/dd ")

    def open_main(self, name: str):
        course = self.courses_obj.get_course(name)
        if course is None:
            print(f"Could not find course: {name}")
        else:
            course.open_main()

    def new_lecture(self):
        pass

    def get_active(self):
        return self.courses_obj.get_active_course()
