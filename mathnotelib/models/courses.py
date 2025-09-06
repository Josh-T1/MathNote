from enum import Enum, auto
from typing import Callable
from math import ceil
from pathlib import Path
from datetime import datetime
import json
import logging

from .source_file import Assignment, FileType, Lecture, StandaloneSourceFile
from ..config import CONFIG, Config

logger = logging.getLogger("mathnote")

def number2filename(num: int, filetype: FileType) -> str:
    return f'lec_{num:02d}{filetype.extension}'


# TODO: refactor this. Some directories are required while some are optional
class Course:
    source_file_directories = [Path("assignments"), Path("main/lectures"), Path("problems"), Path("projects")]
    def __init__(self,
                 path: Path,
                 assignments: list[Assignment] | None=None,
                 lectures: list[Lecture] | None=None,
                 filetype: FileType = FileType.Typst
                 ):
        """
        path: root path to course directory
        """
        self.path = path
        self.filetype = filetype
        self.main_file = StandaloneSourceFile(self.path / "main" / f"main{self.filetype.extension}")
        self.assignments = assignments if assignments is not None else []
        self.lectures = lectures if lectures is not None else []
        self._course_info: dict | None = None

    def pretty_name(self) -> str:
        return self.path.name.replace("-", " ")

    @property
    def name(self):
        return self.path.stem

    def last_edit(self):
        """ Returns time in secods since a lecture file has been edited """
        if not self.lectures:
            return None
        return max([lecture.last_edit() for lecture in self.lectures])

    def lecture_filename_pattern(self) -> str:
        return fr"^lec_\d{{2}}\{self.filetype.extension}$"

    def assignment_filename_pattern(self) -> str:
        return fr"^{self.name}-A\d{{1}}\{self.filetype.extension}$"

    @property
    def course_info(self) -> dict:
        """
        returns: dictionary of course information
        """
        if self._course_info is None:
            self._course_info = self._load_course_info()
        return self._course_info

    def _load_course_info(self) -> dict:
        with open(self.path / "course_info.json", 'r') as f:
            info = json.load(f)

        info["weekdays"] = [] if not info["weekdays"] else self._weekdays_string_to_list(info["weekdays"])
        info["name"] = self.name
        return info

    def this_semester(self) -> bool:
        """
        returns: True if class is active this semester """
        # add logging
        end_date = self.course_info.get("end-date", "")
        if not end_date:
            return False
        return datetime.strptime(end_date, "%Y-%m-%d") > datetime.today()

    @staticmethod
    def _weekdays_string_to_list(data: str):
        return [day.strip() for day in data.split(",")]

    def start_time(self) -> datetime |  None:
        """
        returns: course start time as datetime.datetime object if start time is found, otherwise returns None
        """
        if (start_time := self.course_info["start-time"]):
            return datetime.strptime(start_time, "%H:%M")
        return None

    def end_time(self) -> datetime | None:
        """
        returns: course end time as datetime.datetime object if found, otherwise return None
        """
        if (end_time := self.course_info["end-time"]):
            return datetime.strptime(end_time, "%H:%M")
        return None

    def days(self):
        """ Weekdays zero indexed, starting with Monday """
        weeday_int_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
        try:
            res = [int(weeday_int_map[day]) for day in self.course_info["weekdays"]]
        except KeyError:
            logger.warning("Invalid 'Weeday' in course_info.json file")
            res = []
        return res

    def get_week(self, lecture: Lecture) -> int:
        """
        TODO: week can not be determined without additional info of schedule
        returns: the week as int (1 indexed).
        * returns 0 when week can not be determined from lecture object
        """
        if len(self.days()) == 0:
            return 0
        return ceil(lecture.number() / len(self.days()))

    # adjust this
    def include_template(self) -> Callable[[str], str]:
        if self.filetype == FileType.LaTeX:
            template_func = lambda name: r'\input{lectures/' + name + "}\n"
        else:
            template_func = lambda name: f'#include "{name}"'
        return template_func

    def next_lecture_path(self) -> Path:
        num = 1 if not self.lectures else self.lectures[-1].number() + 1
        new_lecture_path = self.main_file.path.parent / "lectures" / number2filename(num, self.filetype)
        return new_lecture_path

    # TODO
    def new_lecture_template(self) -> str:
        return ""

    def add_lecture(self, lecture: Lecture):
        self.lectures.append(lecture)

    def add_assignment(self, assignment: Assignment):
        self.assignments.append(assignment)

    def next_assignment_path(self) -> Path:
        new_num = max([lec.number() for lec in self.lectures]) + 1
        filename = f"{self.name}-A{new_num}{self.filetype.extension}"
        path = self.path / "assignments" / filename
        return path

    def __eq__(self, other):
        if not isinstance(other, Course):
            return False
        return self.path == other.path

    def __repr__(self) -> str:
        return f"{self.__class__}(path={self.path}, lectures={self.lectures})"
    #TODO: delete, make sure I never use this first
    def __contains__(self, other) -> bool:
        if not isinstance(other, Lecture):
            return False
        for lecture in self.lectures:
            if lecture == other:
                return True
        return False
