import os
from abc import ABC, abstractmethod
from course.lectures import LatexParser
from courses import Courses, Course
from pathlib import Path
from utils import load_json, dump_json
import logging
from typing import Union, final
import shutil
import glob

# cmd type ->
# Have map for command type, try curring
class CliController(ABC):
    def __init__(self, project_config: dict) -> None:
        self.project_config = project_config
        self.courses_obj = Courses(self.project_config)
        self._logger = logging.getLogger(__name__)

    @final
    def get_active(self):
        return self.courses_obj.get_active_course()

    @abstractmethod
    def handle_cmd(self, namespace):
        pass

    @final
    def get_course_info(self, arg: str) -> Union[None, list[dict]]:
        """ Make sure this works
        :TODO Make the logic less retarted, change how buetify output works
        """
        if arg == 'all':
            info = [course.course_info for course in self.courses_obj.courses.values()]
        elif arg == 'recent':
            info = [list(self.courses_obj.courses.values())[-1].course_info] # I pray no one ever sees this attrocitie
        else:
            info = self.courses_obj.courses.get(arg, None)
            info = info if info is None else [info.course_info]
        return info


class ClassCommand(CliController):
    def __init__(self, project_config):
        super().__init__(project_config)

    def handle_course_create(self, namespace):
        name = namespace.name
        if not name:
            raise UserWarning("Tried creating class without inputing name")
        self._logger.debug(f"Creating class with name: {name}")
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

    def handle_active(self):
        self._logger.debug("Finding active class")
        active = self.get_active()
        if isinstance(active, Course):
            active = active.name

    def handle_cmd(self, namespace):
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
        dic = load_json(path)
        for key, val in dic.items():
            if val:
                continue

            print(f"Input value for key: {key}")
            self._additional_message(key)
            res = input("$ ").strip()
#            self._validate_user_input(res)
            dic[key] = res
        dump_json(path, dic)

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
    """ Relies on bash script using stdout as stdin *** no print statements *** """
    def __init__(self, project_config):
        super().__init__(project_config)

    def handle_cmd(self, namespace):
        """ This needs to be re-organized + does it make sence for debug to overide default behaviour
        TODO: clean up cli logic
        """
        # Order matter!  if debug and clean are specified, only debug is ran. Questionalble I know
        if namespace.debug:
            self.handle_debug(namespace)
        elif namespace.clean:
            # Makes the assumtion you are in the target course directory
            self.handle_debug_clean(namespace)
        else:
            self.handle_open_lecture(namespace)
        # Make this so by default it opens new lecture if last lecture was created in last 12 hours with over rider opetion in cli
#        self.move_to_lecture(lecture_path)
    def handle_debug_clean(self, namespace):
        # make so there are one or more parameters and ...
        name = namespace.name if namespace.name != 'active' else 'all'
        target_dir = self._find_target_dir()
        if target_dir is None:
            self._logger.info(f"Could not find course start path: {namespace.name}")
            return
        debug_files = list(target_dir.debug_dir.glob("*.tex"))
        if name != "all":
            debug_files = [file for file in debug_files if file.name == name] # does this work
        self._make_backup(debug_files, target_dir.backup_dir)
        self._update_lectures(debug_files, target_dir.lectures_dir)
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
        """ This needs to be changed. I need to simply class structes.
        Also get_active my return None and this is not taken into account """
        if namespace.name == 'active':
            class_obj = self.get_active()

        elif namespace.name == 'recent':
            class_obj = None # Make this work

        else:
            class_obj = self.courses_obj.courses.get(namespace.name, None)

        if not self.courses_obj.courses.get(class_obj, None):
            self._logger.info(f"No course available with {namespace.name}")
            return
        if namespace.debug:
            pass
        lecture_path = class_obj.new_lecture().file_path  #type: ignore
        print(lecture_path.parent) # This is important, gives path to bash script


class TexCommand(CliController):
    def __init__(self, project_config):
        super().__init__(project_config)

    def get_all_definitions(self, class_name: str) -> str:
        # Assuming that name is class name
        tex = ""
        course = self.courses_obj.courses.get(class_name, None)
        if course == None:
            return tex

        parser = LatexParser({"definitions": "defin"})

        for lec in course.lectures:
            tex += parser.get_sections(lec.file_path)
        return tex

    def handle_cmd(self, namespace):
        pass

