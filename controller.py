import os
import subprocess
from abc import ABC, abstractmethod
from .course.courses import Courses, Course
import logging
from typing import Union, Protocol
from .global_utils import load_json, dump_json

logger = logging.getLogger("course")

class Command(Protocol):
    def cmd(self, namespace) -> None:
        ...

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
            from .flashcard.window import MainWindow
            from .flashcard.flashcard_model import FlashcardModel, TexCompilationManager
            from .flashcard.controller import FlashcardController
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
        window.setCloseCallback(controller.close)
        controller.run(self._app)
        if not flashcard_model.compile_thread.stopped(): # Cant remember if I actually need this
            flashcard_model.compile_thread.wait_for_stop()

class ClassCommand(Command):
    """ Class command """
    def __init__(self, project_config):
        self.project_config = project_config
        self.courses_obj = Courses(self.project_config)

    def handle_course_create(self, namespace):
        name = namespace.name
        if not name:
            raise ValueError("Attempted to create class without name")
        logger.info(f"Creating class with name: {name}")
        self.courses_obj.create_course(name)
        if namespace.user_input:
            self._get_user_input(self.courses_obj.courses[name])

    def handle_course_information(self, namespace):
        arg = namespace.name if namespace.name else 'all'
        info = self.get_course_info(arg)
        if info is None:
            print(f"There is no information given arguments: {namespace}")
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
        if namespace.active:
            self.handle_active()

        elif namespace.information:
            self.handle_course_information(namespace)

        elif namespace.create:
            self.handle_course_create(namespace)

        else:
            raise ValueError(f"Invalid arguments passed: {namespace}")

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

        if "weekday" in key:
            print("Enter a list of comma seperated days for which the course occurs. ie Monday, Tuesday")
        pass

    def get_course_info(self, arg: str) -> Union[None, list[dict]]:
        """
        TODO: Make sure this works
        """
        if arg == 'all':
            info = [course.course_info for course in self.courses_obj.courses.values()]
        elif arg == 'recent':
            info = [list(self.courses_obj.courses.values())[-1].course_info]
        else:
            info = self.courses_obj.courses.get(arg, None)
            info = None if info is None else [info.course_info]
        return info

    def get_active(self):
        return self.courses_obj.get_active_course()
