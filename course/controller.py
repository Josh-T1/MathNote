import os
from abc import ABC, abstractmethod
from courses import Courses, Course
from pathlib import Path
import logging
from typing import Union
import shutil
import glob

class CliController(ABC):
    def __init__(self, project_config: dict) -> None:
        self.project_config = project_config
        self.courses_obj = Courses(self.project_config)
        self._logger = logging.getLogger(__name__)

    def get_active(self):
        return self.courses_obj.get_active_course()

    @abstractmethod
    def cmd(self, namespace):
        pass

    def get_course_info(self, arg: str) -> Union[None, list[dict]]:
        """ Make sure this works
        :TODO Make the logic less retarted, change how buetify output works
        """
        if arg == 'all':
            info = [course.course_info for course in self.courses_obj.courses.values()]
        elif arg == 'recent':
            info = [list(self.courses_obj.courses.values())[-1].course_info]
        else:
            info = self.courses_obj.courses.get(arg, None)
            info = None if info is None else [info.course_info]
        return info

class FlashcardCommand(CliController):
    """ Command for generating flashcards from latex """
    _app = None
    _window = None
    _model = None
    _compilation_manager = None
    _controller = None
    _config = None

    @classmethod
    def _ensure_import(cls):
        if cls._app is None or cls._window is None or cls._model is None or cls._compilation_manager is None or cls._controller is None:
            from PyQt6.QtWidgets import QApplication
            from ..gui.window import MainWindow
            from ..gui.flashcard_model import FlashcardModel, TexCompilationManager
            from ..gui.controller import FlashcardController
            from ..global_utils import get_config
            cls._app = QApplication([])
            cls._window = MainWindow
            cls._model = FlashcardModel
            cls._compilation_manager = TexCompilationManager
            cls._controller = FlashcardController
            cls._config = get_config()

    def __init__(self, project_config: dict):
        super().__init__(project_config)
        self._ensure_import()

    def cmd(self, namespace):
        compilation_manager = self._compilation_manager() #type: ignore
        flashcard_model = self._model(compilation_manager) #type: ignore
        window = self._window() #type: ignore
        controller = self._controller(window, flashcard_model, self._config) #type: ignore
        window.setCloseCallback(controller.close)
        controller.run(self._app)
        if not flashcard_model.compile_thread.stopped(): # Cant remember if I actually need this
            flashcard_model.compile_thread.wait_for_stop()

class ClassCommand(CliController):
    """ Class command """
    def __init__(self, project_config):
        super().__init__(project_config)

    def handle_course_create(self, namespace):
        name = namespace.name
        if not name:
            raise UserWarning("Attempted to create class without name")
        self._logger.info(f"Creating class with name: {name}")
        self.courses_obj.create_course(name)
        if namespace.user_input:
            self._get_user_input(self.courses_obj.courses[name])

    def handle_course_information(self, namespace):
        arg = namespace.name if namespace.name else 'all'
        info = self.get_course_info(arg)
        if info is None:
            print(f"There is no information given the arguments: {namespace}")
            return
        for dic in info:
            print(self.buitify_output(dic))
            print("="*20)

    def handle_active(self) -> str | None:
        self._logger.debug("Finding active class")
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
            raise UserWarning(f"Invalid arguments passed: {namespace}")

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

class LecCommand(CliController):
    """ This entire class can probably be removed """
    """ Relies on bash script using stdout as stdin *** no print statements ***
    This needs a re design. Debug funcitonality can probably be removed"""
    def __init__(self, project_config):
        super().__init__(project_config)

    def handle_cmd(self, namespace):
        """ This needs to be re-organized + does it make sence for debug to overide default behaviour
        TODO: clean up cli logic
        """
        # Order matters!  if debug and clean are specified, only debug is ran. Questionalble I know
        if namespace.debug:
            self.handle_debug(namespace)
#        elif namespace.clean:
#            # Makes the assumtion you are in the target course directory
#            self.handle_debug_clean(namespace)
        else:
            self.handle_open_lecture(namespace)
        # Make this so by default it opens new lecture if last lecture was created in last 12 hours with over rider opetion in cli
#        self.move_to_lecture(lecture_path)

    def handle_debug_clean(self, namespace):
        name = namespace.name if namespace.name != 'active' else 'all'
        target_dir = self._find_target_dir()
        if target_dir is None:
            self._logger.info(f"Could not find course start path: {namespace.name}")
            return
        debug_files = list(target_dir.debug_path.glob("*.tex"))
        if name != "all":
            debug_files = [file for file in debug_files if file.name == name] # does this work
        self._make_backup(debug_files, target_dir.backup_path)
        self._update_lectures(debug_files, target_dir.lectures_path)
        self.detete_files_by_stem(debug_files)

    def detete_files_by_stem(self, files: list[Path]):
        for file in files:
            del_files = glob.glob(f"{file.stem}.*")
            for f in del_files:
                self._logger.info(f"Deleting file: {file}")
                os.remove(f)

    def _make_backup(self, files: list, backup_dir: Path):
        for file in files:
            self._logger.info(f"Copying {file} to backup dir")
            shutil.copy(file, backup_dir / self.debug_to_lecture_name(file))

    @staticmethod
    def debug_to_lecture_name(filename: Path):
        return str(filename.name).split('-')[1]

    def _update_lectures(self, lectures: list[Path], lecture_dir: Path):
        for lecture in lectures:
            header, body, footer = Course.get_header_footer(lecture, end_body_pattern=r'\end{document}', end_header_pattern=r'\begin{document}')
            path = lecture_dir / self.debug_to_lecture_name(lecture)
            path.write_text(body)

    def _find_target_dir(self) -> Union[Course, None]:
        path = Path(os.getcwd())
        for course in self.courses_obj.courses.values():
            if course.path == path or course.path == path.parent:
                return course
        return None

    def handle_debug(self, namespace):
        """ These methods are used by debug which is a faily useless feature... """
        # check if name is path or are u in said directory, this assumes you are in the correct directory
        target_course = self._find_target_dir()

        if target_course is None:
            self._logger.info(f"Could not find course given start path: {namespace.name} ")
            return

        target_lecture = None

        for lecture in target_course.lectures:
            if namespace.name == lecture.name:
                target_lecture = lecture
                break

        if target_lecture is None:
            self._logger.info(f"Could not find {namespace.name} for course {target_course.name}")
            return

        body = target_lecture.file_path.read_text()
        target_path = target_course.debug_dir / f"debug-{target_lecture.name}"
        self._logger.info(f"Copying lecture-template to location: {target_path}")
        shutil.copy(self.project_config["lecture-template"] ,target_path)
        header, body, footer = Course.get_header_footer(target_path, end_body_pattern="\\end{document}", end_header_pattern="\\start{document}")
        self._logger.info("Writting text to debug file")
        target_path.write_text(header + body + footer)


    def handle_open_lecture(self, namespace) -> Union[Path, None]:
        """
        TODO: IFIXLASJFLDJLKSJFlj
        This needs to be changed. I need to simply class structes.
        Also get_active my return None and this is not taken into account """
        if namespace.name == 'active':
            class_obj = self.get_active()

        elif namespace.name == 'recent':
            class_obj = None # Make this work

        else:
            class_obj = self.courses_obj.courses.get(namespace.name, None)

        if not class_obj:
            self._logger.info(f"No course available with {namespace.name}")
            return
        if namespace.debug:
            pass
        lecture_path = class_obj.new_lecture().path
        print(lecture_path.parent) # This is important, gives path to bash script


