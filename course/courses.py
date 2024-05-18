from typing import Union
from lectures import LATEX_CONFIG, LatexParser, Lecture, number2filename, filename2number
from pathlib import Path
from utils import get_config
import logging
import os
from datetime import datetime
import json
import logging
import shutil
import subprocess

class Lecture():
    def __init__(self, file_path) -> None:
        self.file_path: Path = file_path

    @property
    def number(self) -> int:
        num = str(self.file_path.stem).split("_")[-1].lstrip("0")
        return int(num)

    @property
    def name(self) -> str:
        return self.file_path.name

    @property
    def last_edit(self) -> float:
        """ Returns most recent edit in seconds """
        return self.file_path.stat().st_mtime

def requires_parser(func):

    def wrapper(self, *args, **kwargs):
        if getattr(self, "parser") == None:
            raise UserWarning(f"Attemting to call {func.__name__} before add_tex_parser")
        return func(*args, **kwargs)

    return wrapper

class Course():
    """
    TODO: How do can i determine lecture number in a more reliable way. ie) What if i missed a lecture. Can I somehow incoperate uofc calander
    """
    def __init__(self, path: Path):
        self.path: Path = path
        self.name: str = path.stem
        self.dir_names: list[str] = ["lectures", "debug", "main.tex", "backup"]
        self.lectures_path = path / "lectures"
        self.debug_path = path / "debug"
        self.main_file = path / "main.tex"
        self.backup_path = path / "backup"
        self.course_info: dict = self._load_course_info()
        self._lectures: Union[None, list] = None
        self._logger = logging.getLogger(__name__ + "Course")


    def _load_course_info(self) -> dict:
        with open(self.path / "course_info.json", 'r') as f:
            self._info = json.load(f)

        self._info["weekdays"] = [] if not self._info["weekdays"] else self._string_to_list(self._info["weekdays"])
        self._info["name"] = self.name
        return self._info

    @staticmethod
    def _string_to_list(data: str):
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
                stdout = subprocess.STDOUT, # Or Devnull?
                stderr = subprocess.STDOUT,
                cwd=self.path
                )
        return result.returncode

    def __eq__(self, other):
        if type(other) != type(self): return False
        return self.path == other.path

    def __repr__(self) -> str:
        """ TODO: Make this better """
        return f"{__class__} {self.name}"
    def __contains__(self, other) -> bool:
        if not isinstance(Lecture, other): return False
        return other in self.lectures
    # add dunder in

class Courses():
    def __init__(self, config: dict[str, str]):
        self.config = config
        self.root = Path(config["note-path"])
        self._courses = {}
        self.logger = logging.getLogger(__name__ + "Courses")

    def _find_courses(self, key=lambda c: c.name) -> list[Course]:
        """ TODO: sort by last edited """
        course_directories = [x for x in self.root.iterdir() if x.is_dir() and (x / "course_info.json").is_file] # how does iterdir work
        courses = [Course(course) for course in course_directories]
        return list(sorted(courses, key=key))

    @property
    def courses(self) -> dict[str,Course]:
        """ Should this really return a dict? """
        if self._courses:
            return self._courses
        course_list = self._find_courses(key=lambda c: (c.last_edit is not None, c.last_edit))
        return {obj.name: obj for obj in course_list}

    def get_active_course(self, tolerance=10) -> Union[None, Course]:
        """ tolerance: maximum number of minutes for which a class with start_time = 'x' will be considered active at time ('x' - tolerance)
        TODO: test this """

        for course in self.courses.values():
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
        course = self.courses.get(name, None)
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
