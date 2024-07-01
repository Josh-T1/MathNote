from typing import Union
from math import ceil
#from .lectures import LATEX_CONFIG, LatexParser, Lecture, number2filename, filename2number
from .utils import number2filename
from pathlib import Path
#from utils import get_config
import logging
import os
from datetime import datetime
import json
import logging
import shutil
import subprocess
"""
This module could probably use some testing and a re write...
"""
class Lecture():
    def __init__(self, file_path) -> None:
        self.path: Path = file_path

    @property
    def number(self) -> int:
        num = str(self.path.stem).split("_")[-1].lstrip("0")
        return int(num)

    @property
    def name(self) -> str:
        return self.path.name
    @property
    def last_edit(self) -> float:
        """ Returns most recent edit in seconds """
        return self.path.stat().st_mtime

class Course():
    """
    Represents university course
    """
    def __init__(self, path: Path):
        self.path: Path = path
        self.name: str = path.stem
#        self.dir_names: list[str] = ["lectures", "debug", "backup"]
        self.lectures_path = path / "lectures"
        self.debug_path = path / "debug"
        self.main_file = path / "main.tex"
        self.backup_path = path / "backup"
        self._course_info: dict | None = None
        self._lectures: Union[None, list] = None
        self._logger = logging.getLogger(__name__ + "Course")


    @property
    def last_edit(self):
        if not self.lectures:
            return None
        return max([lecture.last_edit for lecture in self.lectures])

    @property
    def course_info(self):
        if self._course_info is None:
            self._course_info = self._load_course_info()
        return self._course_info

    def _load_course_info(self) -> dict:
        with open(self.path / "course_info.json", 'r') as f:
            self._info = json.load(f)

        self._info["weekdays"] = [] if not self._info["weekdays"] else self._weekdays_string_to_list(self._info["weekdays"])
        self._info["name"] = self.name
        return self._info

    @property
    def this_semester(self) -> bool:
        """ returns True if this class is active this semester """
        # add logging
        end_date = self._info.get("end-date", "")
        if not end_date:
            return False
        return datetime.strptime(end_date, "%Y-%m-%d") > datetime.today()

    @staticmethod
    def _weekdays_string_to_list(data: str):
        return [day.strip() for day in data.split(",")]

    @property
    def lectures(self) -> list[Lecture]:
        if self._lectures is not None:
            return self._lectures
        files = self.lectures_path.glob('lec_*.tex')
        self._lectures = sorted((Lecture(f) for f in files), key=lambda l: l.number)
        return self._lectures


    @property
    def start_time(self) -> Union[datetime, None]:
        """ Returns time as datetime.datetime object """
        if self.course_info["start-time"]:
            return self.string_to_time(self.course_info["start-time"])
        return None

    def string_to_time(self, string: str, format="%H:%M") -> datetime:
        return datetime.strptime(string, format)

    @property
    def end_time(self) -> Union[datetime, None]:
        """ Returns time as datetime.datetime object """
        if self.course_info["end-time"]:
            return self.string_to_time(self.course_info["end-time"])
        return None

    @property
    def days(self):
        """ Weekdays zero indexed starting with Monday """
        weeday_int_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4}
        try:
            res = [int(weeday_int_map[day]) for day in self.course_info["weekdays"]]
            return res
        except KeyError:
            self._logger.warning("Invalid 'Weeday' in course_info.json file")
            return []

    @staticmethod
    def get_header_footer(filepath: Path, end_header_pattern="start_lectures", end_body_pattern="end lectures") -> tuple[str, str, str]:
        """ Copy header and footer from main.tex, includes line with end_(header/footer)_pattern in header and footer respectively """
        part = "header"
        header, footer, body = '', '', ''

        with filepath.open() as f:
            for line in f:
                if end_body_pattern in line:
                    part = 'footer'

                if part == 'header':
                    header += line

                if part == 'footer':
                    footer += line

                if part == "body":
                    body += line

                if end_header_pattern in line:
                    part = "body"

        return (header, body, footer)

    def parse_lecture_range(self, string: str) -> int:
        """ TODO: Write discription """
        if string.isdigit():
            return int(string)
        elif string == "last":
            return self.lectures[-1].number
        elif string == 'prev':
            return self.lectures[-1].number -1
        else:
            return 0

    def get_week(self, lecture: Lecture) -> int:
        """ Returns the week as int (1 indexed).
        *** Returns 0 when week can not be determined from lecture object
        """
        if len(self.days) == 0:
            return 0
        return ceil(lecture.number / len(self.days))

    def update_lectures_in_master(self, lecture_nums: list[int]) -> None:
        """ Copy contents of main.tex header and footer, find all lecuteres and their correspoding number, join file parts together
        and write to main.tex
        """
        self._logger.debug("Updating master file")
        header, body, footer = self.get_header_footer(self.main_file)
        body = ''.join(r'\input{lectures/' + number2filename(number) + '}\n' for number in lecture_nums)
        self.main_file.write_text(header + body + footer)

    def new_lecture(self):
        """ Creates a new lecture. Not sure if that has every been 'tested' """
        new_lecture_number = 1 if not self.lectures else self.lectures[-1].number +1

        new_lecture_path = self.lectures_path / number2filename(new_lecture_number)

        self._logger.info(f"Creating lecture: {new_lecture_path}")
        new_lecture_path.touch() # Copy file template instead of touch?
#        new_lecture_path.write_text(f'\\{{lecture{{{new_lecture_number}}}}}\n')
        self._logger.info("Updating main tex file")
        self.update_lectures_in_master([new_lecture_number]) # [new_lecture_number-1, new_lecture_number] when num!=1,  why?

        new_lecture = Lecture(new_lecture_path)
        new_lecture.file_path.write_text(fr'\section*{{Lecture {new_lecture.number}}}')
        if self._lectures is None:
            self._lectures = []
        self.lectures.append(new_lecture)
        return new_lecture

    def compile_main(self):
        # Do i need to convert Path obj's to str? probably not
        self._logger.debug(f"Attempting to compile {self.main_file}")
        result = subprocess.run(
                ['latexmk', '-f', '-interaction=nonstopmode', str(self.main_file)],
                stdout = subprocess.STDOUT,
                stderr = subprocess.STDOUT,
                cwd=self.path
                )
        return result.returncode

    def __eq__(self, other):
        if type(other) != type(self):
            return False
        return self.path == other.path

    def __repr__(self) -> str:
        """ TODO: Make this better """
        return f"{__class__}({self.path})"

    def __contains__(self, other) -> bool: # Make sure isinstance is corrent... backwards args?
        if not isinstance(Lecture, other):
            return False
        return other in self.lectures
    # add dunder in

class Courses():
    def __init__(self, config: dict[str, str]):
        self.config = config
        self.root = Path(config["note-path"])
        self._courses = {}
        self.logger = logging.getLogger("Courses")

    def _find_courses(self, _key = lambda c: c.name) -> list[Course]:
        """ TODO: sort by last edited """
        course_directories = [x for x in self.root.iterdir() if x.is_dir() and (x / "course_info.json").is_file] # how does iterdir work
        courses = [Course(course) for course in course_directories]
        return list(sorted(courses, key=_key))

    def get_course(self, name: str):
        return self.courses().get(name)

    def courses(self) -> dict[str,Course]:
        """ Should this really return a dict? """
        if self._courses:
            return self._courses
        course_list = self._find_courses(_key=lambda course: (course.last_edit is not None, course.last_edit))
        return {obj.name: obj for obj in course_list}

    def get_active_course(self, tolerance=10) -> Union[None, Course]:
        """ tolerance: maximum number of minutes for which a class with start_time = 'x' will be considered active at time ('x' - tolerance)
        TODO: test this """

        for course in self.courses().values():
            time_now = datetime.now()
            if time_now.weekday() not in course.days or course.start_time is None or course.end_time is None:
                continue
            # course_start == None is handled above
            time_difference = course.start_time - time_now # type: ignore
            time_difference_minutes = abs(time_difference.total_seconds() / 60)

            if time_difference_minutes < tolerance or (course.start_time <= time_now <= course.end_time):
                return course
        return None

    def create_course(self, name: str) -> None:
        """
        TODO: copy json file template over, allow flag to indicate weather or not not use user input
        """
        course = self.courses().get(name, None)
        if course == None:
            self.logger.info(f"Failed to create coure: {name} as course already exists")
            return

        course_path = self.root / name
        if course_path.is_dir():
            self.logger.info(f"Course: {name} already exists")
            return

        os.mkdir(course_path)

        make_dirs = ["lectures", "figures", "backup", "debug"] # Add this to config file? link this to dirs in course
        for dir in make_dirs:
            os.mkdir(course_path / dir)

        shutil.copy(self.config["main-template"], course_path / "main.tex")

        template_path = str(Path(__file__).parent / "course_info_template.json") # str conversion is likley unessasary
        shutil.copy(template_path, str(course_path / "course_info.json"))

    # make dict dunder?
    def __contains__(self, course_name):
        if not type(course_name) == type(str): return False
        return course_name in self.courses
