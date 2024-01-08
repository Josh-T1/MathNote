from typing import Union
from lectures import Lectures
from pathlib import Path
from utils import get_config
import logging
import os
from datetime import datetime
import json
import time
import shutil

class Course():
    """ HOW do can i determine lecture number in a more reliable way. ie) What if i missed a lecture. Can I somehowe incoperate uofc calander"""
    def __init__(self, path: Path):
        self.path = path
        self.name = path.stem
        self.course_info = self.course_info()
        self._lectures = None

    def _course_info(self) -> dict:
        with open(self.path / "course_info.json", 'r') as f:
            self._info = json.load(f)
        return self._info

    @property
    def lectures(self) -> Lectures:
        if not self._lectures:
            self._lectures = Lectures(self.path / 'lectures')
        return self._lectures

    @property
    def last_edit(self):
        return min(lecture.last_edit for lecture in self.lectures.lectures)

    @property
    def start_time(self) -> datetime:
        return datetime.strptime(self.course_info["end-time"], "%H:%M")

    @property
    def days(self):
        """ days 0-6 """
        return [int(day) for day in self.course_info["days"]]

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
        self._courses = None
        self.logger = logging.getLogger(__name__ + "Courses")

    def _find_courses(self) -> list[Course]:
        """
        TODO: sort by last edited
        """
        course_directories = [x for x in self.root.iterdir() if x.is_dir()] # how does iterdir work
        courses = [Course(course) for course in course_directories]
        return list(sorted(courses, key=lambda c: c.name))

    @property
    def courses(self) -> dict[str,Course]:
        if self.courses:
            return self.courses
        return dict(obj.name: obj for obj in sorted(self._find_courses(), key=lambda l: l.last_edit))

    def get_active_course(self, tolerance=10) -> Union[None, Course]:
        """ :tolerance in minutes """
        # TODO fileter by day of week that course occurs
        for course in self.courses.values():
            course_time, time_now = course.start_time, datetime.now()

            if time_now.weekday not in course.days:
                continue

            time_diff = abs((time_now.hour * 60 + time_now.minute) - (course_time.hour * 60 + course_time.minute))
            if time_diff < tolerance:
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

        lecture_dir = course_path / "lectures"
        os.mkdir(str(lecture_dir))
        os.mkdir(str(course_path / "figures"))
        (course_path / "main.tex").touch()

        template_path = str(Path(__file__).parent / "course_info_template.json")
        shutil.copy(template_path, str(course_path / "course_info.json"))

    def generate_course_info(self):
        """ User interface for configuring course_info.json. Allow for int or weekday spelling (enum?) """
        raise NotImplementedError

    def get_course(self, name: str) -> Course:
        return self.courses[name]
