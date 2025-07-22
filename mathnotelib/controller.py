from pathlib import Path
import subprocess
import logging
from typing import Protocol
from .utils import load_json, dump_json
from .structure import Courses, Course, NotesManager, Note, NoteType
from .noteviewer import app

logger = logging.getLogger("mathnote")

class Command(Protocol):
    def cmd(self, namespace) -> None: ...


class NoteViewer(Command):
    def __init__(self, project_config: dict):
        self.config = project_config

    def cmd(self, namespace):
        app.run()


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
        # ensure dependencies exist for typst or latex but not necessairly both
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
            from .flashcard import FlashcardModel, CompilationManager, MainWindow, FlashcardController
            cls._app = QApplication([])
            cls._window = MainWindow
            cls._model = FlashcardModel
            cls._compilation_manager = CompilationManager
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
            name, item_type, parent_path = namespace.new_note[0], namespace.note_type[0], namespace.parent[0]
            new_type = {"tex": NoteType.LaTeX, "typ": NoteType.Typst}.get(item_type)

            if parent_path is None:
                parent_cat = notes.root_category
            else:
                parent_cat = notes.root_category.get_subcategory(Path(parent_path))
                if parent_cat is None:
                    print(f"Invalid path for parent category {parent_path}")
                    return

            if new_type is None:
                print(f"Invalid item type {item_type}")

            else:
                notes.new_note(name, parent_cat, new_type)

        elif namespace.new_category:
            name, parent = namespace.new_category[0], namespace.parent[0]
            if parent is None:
                parent = notes.root_category
            else:
                valid_parent = notes.root_category.get_subcategory(parent)
                if valid_parent is False:
                    print(f"Invalid path for parent category {parent}")
                    return
            notes.new_category(name, parent)

        elif namespace.remove_note:
            name, parent = namespace.remove_note[0], namespace.parent[0]
            if parent is None:
                parent = notes.root_category
            else:
                parent = notes.root_category.get_subcategory(parent)
                if parent is None:
                    print(f"Parent category {parent} does not exist")
                    return

            note = notes.get_note(name, parent)
            if note is None:
                print(f"Note {parent.path / name} does not exist")
                return
            try:
                notes.del_note(note)
            except Exception as e:
                print(f"Failed to remove note {parent.path / name}")
                print(e)

        elif namespace.list_notes:
            parent = namespace.parent[0]
            if parent is None:
                parent = notes.root_category
            else:
                parent = notes.root_category.get_subcategory(parent)
                if parent is None:
                    print(f"Parent category {namespace.parent[0]} does not exist")
                    return

            # TODO re-work this
            for note in parent.children:
                if isinstance(note, Note):
                    print(note.name)


        elif namespace.open_note:
            note = notes.get_note(namespace.open_note[0], notes.root_category)
            if note is None:
                print(f"Note {namespace.open_note[0]} does not exist")
            else:
                note.open()
#
        elif namespace.compile_note:
            parent = namespace.parent[0]
            if parent is None:
                parent = notes.root_category
            else:
                parent = notes.root_category.get_subcategory(Path(namespace.parent[0]))
                if parent is None:
                    print(f"Parent category {namespace.parent[0]} does not exist")
                    return
            note = notes.get_note(namespace.compile_note[0], parent)
            if note is None:
                print(f"Note {namespace.compile_note[0]} does not exist")
            else:
                note.compile()

        #TODO need parent category aswell
        elif namespace.rename:
            old_name, new_name, parent = namespace.rename[0], namespace.rename[1], namespace.parent[0]
            if parent is None:
                parent = notes.root_category
            else:
                parent = notes.root_category.get_subcategory(Path(namespace.parent[0]))
                if parent is None:
                    print(f"Parent category {namespace.parent[0]} does not exist")
                    return
            note = notes.get_note(old_name, parent)
            if note is None:
                print(f"Note {parent.path / old_name} does not exist")
                return

            try:
                notes.rename(note, new_name)
            except ValueError as e:
                print(f"Note with name '{new_name}' already exists")

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

        elif namespace.plot_network:
            from PyQt6.QtWidgets import QApplication
            import sys
            # Consider the error when file has never been compiled
#            matrix = notes.build_adj_matrix()
            app = QApplication(sys.argv)
            window = MainWindow()
            window.show()
            sys.exit(app.exec())

