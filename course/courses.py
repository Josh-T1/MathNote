from typing import Union
from lectures import Lectures
from pathlib import Path
from utils import get_config
import logging
import os
from datetime import datetime
import json
import logging
import shutil

class Course():
    """
    TODO: HOW do can i determine lecture number in a more reliable way. ie) What if i missed a lecture. Can I somehowe incoperate uofc calander
    """
    def __init__(self, path: Path):
        self.path = path
        self.name = path.stem
        self.course_info = self._course_info()
        self._lectures = None
        self._logger = logging.getLogger(__name__ + "Course")

    def _course_info(self) -> dict:
        with open(self.path / "course_info.json", 'r') as f:
            self._info = json.load(f)
        # This is how the mentally challanged try to handle 'list' data in json
        self._info["weekdays"] = self._info["weekdays"] if self._info["weekdays"] else self._string_to_list(self._info)
        self._info["name"] = self.name
        return self._info

    @staticmethod
    def _string_to_list(data: str):
        """
        TODO: Figure out a less retarted way to get list from json, change how user input is saved to json file?
        """
        return [day.split() for day in data.split(",")]

    @property
    def lectures(self) -> Lectures:
        if not self._lectures:
            self._lectures = Lectures(self.path / 'lectures')
        return self._lectures

    @property
    def last_edit(self):
        if self.lectures.lectures:
            return min(lecture.last_edit for lecture in self.lectures.lectures)
        return None

    @property
    def start_time(self) -> datetime:
        return datetime.strptime(self.course_info["end-time"], "%H:%M")

    @property
    def days(self):
        """ days 0-6 """
        weeday_int_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4}
        try:
            res = [int(weeday_int_map[day]) for day in self.course_info["weekdays"]]
            return res
        except KeyError:
            self._logger.warning("Invalid 'Weeday' in course_info.json file")
            return []

    @property
    def end_time(self) -> datetime:
        return datetime.strptime(self.course_info["start-time"], "%H:%M")

    def __eq__(self, other):
        if type(other) != type(self):
            return False
        return self.path == other.path

    def __repr__(self) -> str:
        return f"{__class__} {self.name}"

class Courses():
    """ Find courses and build Course objects"""
    # Find current runing class
    def __init__(self, config: dict[str, str]):
        self.config = config
        self.root = Path(config["note-path"])
        self._courses = {}
        self.logger = logging.getLogger(__name__ + "Courses")

    def _find_courses(self, key=lambda c: c.name) -> list[Course]:
        """
        TODO: sort by last edited
        """
        course_directories = [x for x in self.root.iterdir() if x.is_dir()] # how does iterdir work
        courses = [Course(course) for course in course_directories]
        return list(sorted(courses, key=key))

    @property
    def courses(self) -> dict[str,Course]:
        if self._courses:
            return self._courses
        course_list = self._find_courses(key=lambda c: (c.last_edit is not None, c.last_edit))
        return {obj.name: obj for obj in course_list}

    def get_active_course(self, tolerance=10) -> Union[None, Course]:
        """ :tolerance in minutes
        :**** VERIFY THIS WORKS
        """
        # TODO fileter by day of week that course occurs
        for course in self.courses.values():
            course_time, time_now = course.start_time, datetime.now()

            if time_now.weekday not in course.days:
                continue

            time_diff = abs((time_now.hour * 60 + time_now.minute) - (course_time.hour * 60 + course_time.minute))
            if time_diff < tolerance or (course.start_time <= time_now <= course.end_time):
                return course
        return None

    def create_course(self, name: str) -> None:
        """
        TODO: copy json file template over, allow flag to indicate weather or not not use user input
        """
        course_path = self.root / name
        if course_path.is_dir():
            self.logger.info(f"Course: {name} already exists")
            return
        os.mkdir(course_path)
        lecture_dir = course_path / "lectures"
        os.mkdir(lecture_dir)
        os.mkdir(course_path / "figures")
        (course_path / "main.tex").touch()

        template_path = str(Path(__file__).parent / "course_info_template.json") # str conversion is likley unessasary
        shutil.copy(template_path, str(course_path / "course_info.json"))

    def get_course(self, name: str) -> Union[Course, None]:
        """ THis seems gay and unessasary """
        try:
            info = self.courses[name]
            return info
        except KeyError:
            self.logger.info(f"Invalid course name: {name}")
            return None

    def lecture_exists(self, path) -> bool:
        """ This is gay and sucks. There are way to many layers of abstraction that add no value """
        if not isinstance(path, Path):
            return False
        paths = [lecture.file_path for course in self.courses.values() for lecture in course.lectures.lectures]
        return path in paths
