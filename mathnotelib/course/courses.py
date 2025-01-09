from typing import Union
from math import ceil
from pathlib import Path
import os
import re
from datetime import datetime
import json
import logging
import shutil
import subprocess
from ..utils import open_cmd


logger = logging.getLogger("course")

def number2filename(n: int):
    return 'lec_{0:02d}.tex'.format(n)

def filename2number(s: str):
    return int(s.replace('.tex', '').replace('lec_', '').lstrip("0"))

class Lecture():
    def __init__(self, file_path: Path) -> None:
        if not isinstance(file_path, Path):
            raise ValueError("file path must be type 'Path'")
        self.path = file_path

    def number(self) -> int:
        """" returns: lecture number """
        num = filename2number(str(self.path.name))
        return num

    def name(self) -> str:
        """ lecture file name. e.g lec_01.tex """
        return self.path.name

    def last_edit(self) -> float:
        """ Returns most recent edit in seconds """
        return self.path.stat().st_mtime

    def __eq__(self, other):
        if not isinstance(other, Lecture):
            return False
        return other.path == self.path

class Course:
    """
    Represents university course
    """
    def __init__(self, path: Path):
        """
        path: root path to course directory
        """
        self.path = path
        self.name: str = path.stem
        self.main_path = path / "main"
        self.assignment_path = path / "assignments"
        self.lectures_path = self.main_path / "lectures"
        self._course_info: dict | None = None
        self._lectures: None | list[Lecture] = None


    def last_edit(self):
        """ Returns time in secods since a lecture file has been edited """
        if not self.lectures:
            return None
        return max([lecture.last_edit() for lecture in self.lectures])

    def open_main(self):
        if not (self.main_path / "main.pdf").is_file():
        #compile everytime?
            self.compile_main()
        open = open_cmd()
        subprocess.run([open, f"{self.main_path / 'main.pdf'}"], stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL)

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

    @property
    def lectures(self) -> list[Lecture]:
        if self._lectures is not None:
            return self._lectures
        files = self.lectures_path.glob('lec_*.tex')
        self._lectures = sorted((Lecture(f) for f in files), key=lambda l: l.number())
        return self._lectures

    def start_time(self) -> Union[datetime, None]:
        """
        returns: course start time as datetime.datetime object if start time is found, otherwise returns None
        """
        if (start_time := self.course_info["start-time"]):
            return datetime.strptime(start_time, "%H:%M")
        return None


    def end_time(self) -> Union[datetime, None]:
        """
        returns: course end time as datetime.datetime object if found, otherwise return None """
        if (end_time := self.course_info["end-time"]):
            return datetime.strptime(end_time, "%H:%M")
        return None

    def days(self):
        """ Weekdays zero indexed, starting with Monday """
        weeday_int_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4}
        try:
            res = [int(weeday_int_map[day]) for day in self.course_info["weekdays"]]
        except KeyError:
            logger.warning("Invalid 'Weeday' in course_info.json file")
            res = []
        return res

    @staticmethod
    def get_header_footer(filepath: Path, end_header_pattern: str = "start_lectures", end_body_pattern: str = "end lectures") -> tuple[str, str, str]:
        """ Copy header and footer from main.tex, includes line with end_(header/footer)_pattern in header and footer respectively
        -- Params --
        filepath: path to file
        end_header_pattern: pattern signaling preamble is terminating in main.tex
        end_body_pattern: pattern signaling last lecture to be included in main.tex
        returns: (header, body, footer)
        """
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
        """ TODO: is this still used? """
        if string.isdigit():
            return int(string)
        elif string == "last":
            return self.lectures[-1].number()
        elif string == 'prev':
            return self.lectures[-1].number() -1
        else:
            return 0

    def get_week(self, lecture: Lecture) -> int:
        """
        TODO: week can not be determined without additional info of schedule
        returns: the week as int (1 indexed).
        * returns 0 when week can not be determined from lecture object
        """
        if len(self.days()) == 0:
            return 0
        return ceil(lecture.number() / len(self.days()))

    def update_lectures_in_master(self, lecture_nums: list[int]) -> None:
        """ Update main.tex with new lectures
        lecture_nums: list of all numbers corresponds to a lecture
        """
        mainTex = self.main_path / "main.tex"
        logger.debug("Updating main.tex")
        header, body, footer = self.get_header_footer(mainTex)
        body = ''.join([r'\input{lectures/' + number2filename(number) + '}\n' for number in lecture_nums])
        mainTex.write_text(header + body + footer)

    def new_lecture(self):
        """ Creates a new lecture """
        new_lecture_number = 1 if not self.lectures else self.lectures[-1].number() + 1
        new_lecture_path = self.lectures_path / number2filename(new_lecture_number)

        logger.info(f"Creating lecture: {new_lecture_path}")
        new_lecture_path.touch() # Copy file template instead of touch?
#        new_lecture_path.write_text(f'\\{{lecture{{{new_lecture_number}}}}}\n')
        logger.debug("Updating main.tex file")
        self.update_lectures_in_master([i for i in range(1, new_lecture_number + 1)]) # TODO test

        new_lecture = Lecture(new_lecture_path)
        new_lecture.path.write_text(fr'\section*{{Lecture {new_lecture.number}}}')
        self.lectures.append(new_lecture)
        return new_lecture

    def new_assignment(self):
        files = [str(file) for file in self.assignment_path.glob('*.tex')]
        nums = []
        for file in files:
            nums.extend([e for e in re.split("[^0-9]", file)])
#        max = max([int(i) for i in nums])
        # list assignments
        # Get largest number
        # increment by one
        # copy tempalte to name
        pass

    def compile_main(self, lectures_only: bool=False):
        """ Compile main file
        lectures_only: If True pdf will only contain lecture notes, otherwise endnotes and prelimanary sections
        will be included
        returns: error code. e.i {0, 1}
        """
        mainTex = self.main_path / "main.tex"
        logger.debug(f"Attempting to compile {mainTex}")
        result = subprocess.run(
                ['latexmk', '-f', '-pdflatex="pdflatex -interaction=nonstopmode"', str(mainTex)],
                stdout = subprocess.DEVNULL,
                stderr = subprocess.DEVNULL,
                cwd=self.path
                )
        return result.returncode

    def __eq__(self, other):
        if not isinstance(other, Course):
            return False
        return self.path == other.path

    def __repr__(self) -> str:
        return f"{__class__}(path={self.path}, lectures={self.lectures})"

    def __contains__(self, other) -> bool:
        if not isinstance(other, Lecture):
            return False
        for lecture in self.lectures:
            if lecture == other:
                return True
        return False


class Courses():
    """ Container for all Course objects """
    def __init__(self, config: dict[str, str]):
        self.config = config
        self.root = Path(config["note-path"])
        self._courses = {}

    def _find_courses(self, _key = lambda c: c.name) -> list[Course]:
        """ TODO: sort by last edited
        _key: key for sorting course objects. Default key is sort by name
        returns: list of courses sorted by _key
        """
        course_directories = [x for x in self.root.iterdir() if x.is_dir() and (x / "course_info.json").is_file()]
        courses = [Course(course) for course in course_directories]
        return list(sorted(courses, key=_key))

    def get_course(self, name: str) -> Course | None:
        return self.courses.get(name, None)

    @property
    def courses(self) -> dict[str,Course]:
        """
        returns: dict with the key value pairs, (course name, course object)
        """
        if self._courses:
            return self._courses
        course_list = self._find_courses(_key=lambda course: (course.last_edit() is not None, course.last_edit()))
        return {obj.name: obj for obj in course_list}

    def get_active_course(self, tolerance: int = 10) -> Union[None, Course]:
        """
        tolerance: maximum number of minutes for which a class with start_time = 'x' will be considered active at time ('x' - tolerance). e.g If class A starts at 10:00am we consider it activate at 9:50 by default
        returns: active course or None
        """

        for course in self.courses.values():
            time_now = datetime.now()
            start, end = course.start_time(), course.end_time()
            if (time_now.weekday() not in course.days()
                or start is None
                or end is None
                or time_now > end):
                continue

            time_difference = abs(start - time_now)
            time_difference_minutes = time_difference.total_seconds() / 60

            if time_difference_minutes < tolerance or start < time_now:
                return course
        return None

    def create_course(self, name: str) -> None:
        """ Creates directory structure for course, and creates all required files
        -- Params --
        name: name of new course
        """
        course = self.courses.get(name, None)
        # prevent overiding course
        if course != None:
            logger.info(f"Failed to create, course with name={name} already exists")
            raise ValueError(f"Attempting to create course with existing name: {name}")

        course_path = self.root / name
        os.mkdir(course_path)

        make_dirs = ["lectures", "figures", "assignments", "preliminary", "endnotes"] # Add this to config file? link this to dirs in course
        for dir in make_dirs:
            os.mkdir(course_path / dir)

        shutil.copy(self.config["main-template"], course_path / "main.tex")
        template_path = Path(__file__).parent.parent / "templates/course_info_template.json" # str conversion is likley unessasary
        shutil.copy(template_path, course_path / "course_info.json")

    def __contains__(self, course_name: str):
        if not isinstance(course_name, str):
            return False
        return course_name in self.courses
