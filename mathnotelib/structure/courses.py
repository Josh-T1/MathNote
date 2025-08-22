from enum import Enum, auto
import re
from typing import Literal, TypedDict, Union
from math import ceil
from pathlib import Path
from datetime import datetime
import json
import logging
import shutil

from .source_file import FileType, OutputFormat, CompileOptions, SourceFile
from ..utils import Config

logger = logging.getLogger("mathnote")

def number2filename(num: int, filetype: FileType):
    if filetype == FileType.LaTeX:
        return 'lec_{0:02d}.tex'.format(num)
    else:
        return 'lec_{0:02d}.typ'.format(num)

class CourseSubdir(Enum):
    Assignment = auto()
    Lectures = auto()

class Assignment(SourceFile):
    def number(self) -> int:
        pattern = r"-A(\d+)"
        matches = re.findall(pattern, self.path.name)
        if len(matches) == 0:
            return 0
        else:
            return int(matches[-1])

class Lecture(SourceFile):
    def __post_init__(self):
        assert self.file_type() != FileType.Unsupported

    def number(self) -> int:
        """" returns: lecture number """
        num = int(self.path.stem.replace('lec_', '').lstrip("0"))
        return num

    @property
    def name(self) -> str:
        """ lecture file name. e.g lec_01.tex(typ) """
        return self.path.name

    def last_edit(self) -> float:
        """ Returns most recent edit in seconds """
        return self.path.stat().st_mtime


class CompilableCourseFiles(TypedDict):
    main: SourceFile | None
    assignments: list[Assignment]
    lectures: list[Lecture]


class Course:
    def __init__(self, path: Path):
        """
        path: root path to course directory
        """
        self.path = path
        self.name: str = path.stem
        self.typset_files: CompilableCourseFiles = self._load_typset_files()
        self._course_info: dict | None = None

    def _load_typset_files(self) -> CompilableCourseFiles:
        d: CompilableCourseFiles = {"main": None, "assignments": [], "lectures": []}
        main_path = self.path / "main"
        assignment_path = self.path / "assignments"
        lectures_path = main_path / "lectures"

        if (main_file := main_path / "main.tex").exists():
            d["main"] = SourceFile(main_file)
        if assignment_path.exists() and assignment_path.is_dir():
            for p in assignment_path.iterdir():
                if not p.is_file():
                    continue
                if p.suffix in {'.typ', ".tex"}:
                    d["assignments"].append(Assignment(p))
        if lectures_path.exists() and lectures_path.is_dir():
            for p in lectures_path.iterdir():
                if not p.is_file():
                    continue
                if p.suffix in {'.typ', ".tex"}:
                    d["lectures"].append(Lecture(p))
        return d

    #TODO: Rename lecture type
    def lecture_type(self, fallback: FileType=FileType.LaTeX) -> FileType:
        """
        fallback: If filetype key is missing from course_info dict then we default to returning LaTeX
        """
        # Add log message for missing key in .json file
        raw_filetype_str = self.course_info.get("filetype", fallback.value)
        filetype_normalized = raw_filetype_str.upper()
        filetype_map: dict[str, FileType] = {"LATEX": FileType.LaTeX, "TYPST": FileType.Typst, "UNSUPPORTED": FileType.Unsupported}
        filetype = filetype_map.get(filetype_normalized, fallback)
        return filetype

    def last_edit(self):
        """ Returns time in secods since a lecture file has been edited """
        if not self.lectures:
            return None
        return max([lecture.last_edit() for lecture in self.lectures])

    def open_main(self):
        if (main_file := self.typset_files["main"]) is not None:
            main_file.open_pdf()

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
        return self.typset_files["lectures"]

    def start_time(self) -> Union[datetime, None]:
        """
        returns: course start time as datetime.datetime object if start time is found, otherwise returns None
        """
        if (start_time := self.course_info["start-time"]):
            return datetime.strptime(start_time, "%H:%M")
        return None


    def end_time(self) -> Union[datetime, None]:
        """
        returns: course end time as datetime.datetime object if found, otherwise return None
        """
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
    def get_header_footer(filepath: Path, end_header_pattern: str = "begin lectures", end_body_pattern: str = "end lectures") -> tuple[str, str, str]:
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

    def update_lectures_in_main(self) -> None:
        """ Update main file with new lectures
        lecture_nums: list of all numbers corresponds to a lecture
        """
        main_file, lectures = self.typset_files["main"], self.typset_files["lectures"]
        lectures.sort(key=lambda lec: lec.number())

        if main_file is None:
            return

        main_file_path = main_file.path
        header, _, footer = self.get_header_footer(main_file_path)
        if main_file.file_type() == FileType.LaTeX:
            template_func = lambda name: r'\input{lectures/' + name + "}\n"
        else:
            template_func = lambda name: f'#include "{name}"'
        body = ''.join([template_func(lecture.name) for lecture in lectures])
        main_file_path.write_text(header + body + footer)

    def new_lecture(self):
        """ Creates a new lecture """
        main_file = self.typset_files["main"]
        lectures = self.typset_files["lectures"]
        if main_file is None:
            return
        filetype = main_file.file_type()

        new_lecture_number = 1 if not lectures else lectures[-1].number() + 1
        new_lecture_path = main_file.path / "lectures" / number2filename(new_lecture_number, filetype)

        logger.info(f"Creating lecture: {new_lecture_path}")
        new_lecture_path.touch() # Copy file template instead of touch?
#        new_lecture_path.write_text(f'\\{{lecture{{{new_lecture_number}}}}}\n')
        logger.debug("Updating main file")

        new_lecture = Lecture(new_lecture_path)
        new_lecture.path.write_text(fr'\section*{{Lecture {new_lecture.number()}}}')
        self.lectures.append(new_lecture)

        self.update_lectures_in_main() # TODO test
        return new_lecture

    def new_assignment(self, template_path: Path, filetype: FileType = FileType.LaTeX):
        """
        TODO: Refactor using Assignment to hide logic
        Create new assignment using the naming convention course_course_number_A{assignment number}
        """
        assert template_path.is_file()
        new_num = max([lec.number() for lec in self.typset_files["lectures"]]) + 1
        ext = "tex" if filetype == FileType.LaTeX else "typ"
        filename = f"{self.name}-A{new_num}{ext}"
#        template = self.config[filetype][f"assignment_template"]

        assignment_path = self.path / "assignments" / filename
        if assignment_path.is_file():
            raise ValueError
        shutil.copy(template_path, assignment_path)


    def compile_main(self, options: CompileOptions | None = None):
        """ Compile main file
        lectures_only: If True pdf will only contain lecture notes, otherwise endnotes and prelimanary sections
        will be included
        returns: error code. e.i {}
        """

        if (main_file := self.typset_files["main"]) is not None:
            if options is None:
                options = CompileOptions(main_file.path, OutputFormat.PDF)
            result_code = main_file.compile(options)
        else:
            result_code = 1
        return result_code

    def __eq__(self, other):
        if not isinstance(other, Course):
            return False
        return self.path == other.path

    def __repr__(self) -> str:
        return f"{self.__class__}(path={self.path}, lectures={self.lectures})"

    def __contains__(self, other) -> bool:
        if not isinstance(other, Lecture):
            return False
        for lecture in self.lectures:
            if lecture == other:
                return True
        return False

""" Needs refactor """
class Courses():
    """ Container for all Course objects """
    def __init__(self, config: Config):
        self.config = config
        self.root = config.root_path
        self.course_root = self.root / "Courses"
        self._courses: dict[str, Course] = {}

    def _find_courses(self, _key = lambda c: c.name) -> list[Course]:
        """
        _key: key for sorting course objects. Default key is sort by name
        returns: list of courses sorted by _key
        """
        course_directories = [x for x in self.course_root.iterdir() if x.is_dir() and (x / "course_info.json").is_file()]
        courses = [Course(course) for course in course_directories]
        return list(sorted(courses, key=_key))

    def macros_path(self, note_type: FileType = FileType.Typst):
        if note_type == FileType.LaTeX:
            return self.root / "Preambles" / "macros.tex"
        else:
            return self.root / "Preambles" / "macros.typ"

    def preamble_path(self, note_type: FileType = FileType.Typst):
        if note_type == FileType.LaTeX:
            return self.root / "Preambles" / "preamble.tex"
        else:
            return self.root / "Preambles" / "preamble.typ"

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

    def create_course(self, name: str, file_type: FileType = FileType.Typst) -> None:
        """ Creates directory structure for course, and creates all required files
        -- Params --
        name: name of new course
        """
        course = self.get_course(name)
        # prevent overiding course
        if course != None:
            logger.info(f"Failed to create, course with name={name} already exists")
            raise ValueError(f"Attempting to create course with existing name: {name}")

        course_path = self.course_root / name
        course_path.mkdir()

        main_dir = course_path / "main"
        assignments_dir = course_path / "assignments"
        resources_dir = course_path / "resources"
        problems_dir = course_path / "problems"

        main_dir.mkdir()
        assignments_dir.mkdir()
        resources_dir.mkdir()
        problems_dir.mkdir()

        lectures_dir = main_dir / "lectures"
        lectures_dir.mkdir()
        # TODO
        shutil.copy(self.config.template_files[file_type]["main_template"], main_dir / "main.tex")
        template_path = self.config.templates_path / "course_info_template.json"
        if template_path.is_file():
            shutil.copy(template_path, course_path / "course_info.json")
        else:
            logger.warning("TODO")

    def __contains__(self, course_name: str):
        if not isinstance(course_name, str):
            return False
        return course_name in self.courses
