from pathlib import Path
import subprocess
from .course import Courses, Course
import logging
from typing import Protocol
from .utils import load_json, dump_json
from .note import NotesManager

logger = logging.getLogger("mathnote")

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
            from .flashcard import FlashcardModel, TexCompilationManager, MainWindow, FlashcardController
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

class CourseCommand(Command):
    """ Class command """
    def __init__(self, project_config):
        self.project_config = project_config
        self.courses_obj = Courses(self.project_config)

    def create_course(self, namespace):
        logger.info(f"Creating course with name: {namespace.name[0]}")
        self.courses_obj.create_course(namespace.name[0])
        if namespace.user_input is not None:
            self._get_user_input(self.courses_obj.courses[namespace.name[0]])

    def get_course_information(self, name: str):
        course = self.courses_obj.courses.get(name, None)
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

    def cmd(self, namespace):
        if (course:= namespace.name[0]) is None:
            return

        if namespace.new_course:
            self.create_course(namespace)
            return

#        if namespace.current_course:
#            self.handle_active()

        if namespace.information:
            self.get_course_information(course)

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
    def beautify_output(info: dict):
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

    def get_active(self):
        return self.courses_obj.get_active_course()


class NoteCommand(Command):
    """ Command for the creation, management, and visualization of notes """
    def __init__(self, project_config: dict):
        self.config = project_config
        self.note_dir = Path(project_config['root']) / "Notes"

    def cmd(self, namespace):
        notes = NotesManager(self.note_dir)
        if namespace.new_note:
            notes.new_note(namespace.new_note[0])

        elif namespace.remove_note:
            notes.del_note(namespace.remove_note[0])

        elif namespace.list_notes:
            notes.list_notes()

        elif namespace.open_note:
            note = notes.get_note(namespace.open_note[0])
            if note is None:
                print(f"Note {namespace.open_note[0]} does not exist")
            else:
                note.open()

        elif namespace.compile_note:
            note = notes.get_note(namespace.compile_note[0])
            if note is None:
                print(f"Note {namespace.compile_note[0]} does not exist")
            else:
                note.compile()

        elif namespace.rename:
            notes.rename(namespace.rename[0], namespace.rename[1])

        elif namespace.tag:
            note = notes.get_note(namespace.tag[0])
            if note is None:
                print(f"Note {namespace.tag[0]} does not exist")
            else:
                note.add_tag(namespace.tag[1])

        elif namespace.remove_tag:
            note = notes.get_note(namespace.remove_tag[0])
            if note is None:
                print(f"Note {namespace.remove_tag[0]} does not exist")
            else:
                note.remove_tag(namespace.remove_tag[1])

        elif namespace.exists:
            note = notes.get_note(namespace.exists[0])
            if note is None:
                print(f"False")
            else:
                print(f"True")
