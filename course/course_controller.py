from os import name, stat
import lectures
from courses import Courses, Course
from pathlib import Path
from utils import load_json, dump_json
import logging
import subprocess
from typing import Union
# cmd type ->
# Have map for command type, try curring
class CliController():
    def __init__(self, project_config: dict) -> None:
        self.courses_obj = Courses(project_config)
        self._logger = logging.getLogger(__name__)

    def get_active(self):
        self.courses_obj.get_active_course()

    def handle_cmd(self, namespace):
        raise NotImplementedError


    def get_course_info(self, arg: str):
        """ Make sure this works """
        if arg == 'all':
             info = [course.course_info for course in self.courses_obj.courses.values()]
        elif arg == 'recent':
            # works?
            info = list(self.courses_obj.courses.values())[-1].course_info
        else:
            info = self.courses_obj.get_course(arg)
            info = info if info is None else info.course_info
        return info


class ClassCommand(CliController):
    def __init__(self, project_config):
        super().__init__(project_config)

    def handle_cmd(self, namespace):
        if namespace.active:
            self._logger.debug("Finding active class")
            active = self.get_active()
            print(f"Active course: {active}")

        elif namespace.information:
            arg = namespace.name if namespace.name else 'all'
            info = self.get_course_info(arg)
            if info is None:
                print(f"There is no information given the arguments: {namespace}")
                return
            for dic in info:
                print(self.buitify_output(dic))
                print("")

        elif namespace.create:
            if not namespace.name:
                self._logger.info(f"Tried creating class without inputing --name")
                raise ValueError
            self._logger.debug(f"Creating class with name: {name}")
            self.courses_obj.create_course(namespace.name)
            self._get_user_input(self.courses_obj.courses[namespace.name])
        else:
            self._logger.info(f"Invalid arguments passed: {namespace}")
            print("Invalid arguments")

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
    def __init__(self, project_config):
        self.courses_obj = Courses(project_config)

    def handle_cmd(self, namespace):
        if namespace.name == 'active':
            lecture = self.handle_active()
        elif namespace.name == 'recent':
            lecture = None # Make this work
        else:
            lecture = Path(namespace.name)
        if not self.courses_obj.lecture_exists(lecture):
            self._logger.info("No course available with {name}")
            return
        self.open_lecture(lecture) # IGNORE Warining, invalid lecture types are handled above

    def handle_active(self) -> Union[Course, None]:
        """ Attempts to find active course and returns active course or None"""
        active_course = self.get_active()
        if active_course is None:
            return None
        new_lecture = active_course.lectures.new_lecture()
        return new_lecture.path

    def open_lecture(self, lecture_path: Path):
        # Do I need str conversion
        self._logger.debug(f"Attemting to open {lecture_path} with vim")
        subprocess.Popen(["nvim", str(lecture_path)])

