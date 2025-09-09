from pathlib import Path
import json
import shutil
import logging
from datetime import datetime
import re

from ..services import get_header_footer
from ..config import Config
from ..models import Course, Assignment, Lecture
from .._enums import FileType
from ..exceptions import CourseExistsError, InvalidNameError

logger = logging.getLogger(__name__) # TODO

# TODO: I dont want to pass CONFIG to repo
class CourseRepository:
    """ Container for all Course objects """
    _instances: dict[Path, 'CourseRepository'] = {}

    def __init__(self, config: Config):
        if getattr(self, "_initialized", False):
            return
        self.config = config
        self.root = config.root_path
        self.course_root = self.root / "Courses"
        self._initialized = True
        self._courses: dict[str, Course] = {}

    def __repr__(self):
        return f"<CourseRepository root={repr(self.course_root)}>"

    def __new__(cls, config: Config):
        path = config.root_path
        if path not in cls._instances:
            instance = cls._instances[path] = super().__new__(cls)
            instance._initialized = False
            instance._instances[path] = instance
        return cls._instances[path]

    def courses(self, sort: bool=False) -> dict[str,Course]:
        """Returns dict with the key value pairs: (course name, course object)"""
        if not self._courses:
            course_list = self.load_courses(sort=sort)
            self._courses = {obj.name: obj for obj in course_list}
        return self._courses

    #TODO: this should not exist-resolve method this vs course_info.json["filetype"] method
    def _get_course_type(self, path: Path) -> FileType:
        # TODO: check file first + what does it mean for course.filetype = FileType.LaTeX? Lectures only? hard overide for assignments?
        if (path / "main" / "main.tex").is_file():
            return FileType.LaTeX
        return FileType.Typst

    def load_courses(self, sort: bool=False) -> list[Course]:
        """ Load coure objects from directories

        Args:
            _key: key for sorting course objects. By default we sort by name

        Returns: list of Course objects sorted by _key
        """
        def _key(course: Course):
            try:
                num = int(course.name.split("-")[1])
                return num
            except Exception as e:
                return 0
        courses = []
        course_directories = [x for x in self.course_root.iterdir() if x.is_dir() and (x / "course_info.json").is_file()]
        for dir in course_directories:
            ctype = self._get_course_type(dir)
            course = Course(dir, filetype=ctype)
            course.lectures = self._load_lectures(course)
            course.assignments = self._load_assignments(course)
            courses.append(course)
        if sort:
            courses.sort(key=_key)
        return courses

    # TODO should these even be methods?
    def macros_path(self, note_type: FileType = FileType.Typst):
        return self.config.template_files[note_type]["macros"]

    def preamble_path(self, note_type: FileType = FileType.Typst):
        return self.config.template_files[note_type]["preamble"]

    def get_course(self, name: str) -> Course | None:
        return self.courses().get(name, None)

    def get_active_course(self, tolerance: int = 10) -> Course | None:
        """
        Args:
            tolerance: maximum number of minutes for which a class with start_time = 'x' will be considered active at time ('x' - tolerance).
                        e.g If class A starts at 10:00am we consider it activate at 9:50 by default
        Returns:
            course which is currently occuring or None
        """
        for course in self.courses().values():
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

    def create_course(self,
                      name: str,
                      filetype: FileType = FileType.Typst,
                      start_time: str | None=None,
                      end_time: str | None=None,
                      weekdays: list[str] | None=None,
                      start_date: str | None=None,
                      end_date: str | None=None
                      ) -> Course:
        """ Creates directory structure for course, and creates all required files

        Args:
            name: course name (e.g., math-445)
            filetype: setting filetype determines the filetype of all lectures and main file
            start_time: in format 'HH:MM'
            end_time: in format 'HH:MM'
            weekdays: list of weekdays for which the course has lectures
            start_date: in format "yyyy/mm/dd"
            end_date: in format "yyyy/mm/dd"

        Raises:
            CourseExistsError: If course with 'name' already exists
            InvalidNameError: If name is left blank

        Returns:
            New course
        """
        course = self.get_course(name)
        # prevent overiding course
        if course != None:
            logger.info(f"Course '{name}' already exists")
            raise CourseExistsError(f"Course with name '{name}' already exists")
        if not name:
            raise InvalidNameError(f"Name cannot be blank")

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

        shutil.copy(self.config.template_files[filetype]["main_template"], main_dir / f"main{filetype.extension}")
        self._init_course_info(course_path, filetype, start_time, end_time, weekdays, start_date, end_date)
        course = Course(course_path)
        self.courses()[name] = course
        return course

    def _init_course_info(self, course_path: Path,
                      file_type: FileType = FileType.Typst,
                      start_time: str | None=None,
                      end_time: str | None=None,
                      weekdays: list[str] | None=None,
                      start_date: str | None=None,
                      end_date: str | None=None
                          ):
        info_path = course_path / "course_info.json"
        assert course_path.exists() and course_path.is_dir() and not info_path.is_file()

        info_path.touch()
        course_info = {
                "filetype": file_type.value,
                "start_time": start_time if start_time is not None else "",
                "end-time": end_time if end_time is not None else "",
                "weekdays": ",".join(weekdays) if weekdays is not None else "",
                "start-date": start_date if start_date is not None else "",
                "end-date": end_date if end_date is not None else ""
                }
        with info_path.open("w") as f:
            json.dump(course_info, f, indent=4)

    def delete_course(self, course: Course) -> None:
        dir = course.path
        shutil.rmtree(dir)
        del self.courses()[course.name]

    def __contains__(self, course_name: str):
        if not isinstance(course_name, str):
            return False
        return course_name in self.courses().keys()


    def create_assignment(self, course: Course) -> Assignment:
        new_path = course.next_assignment_path()
        assert not new_path.exists() and new_path.parent.exists()
        template_path = self.config.template_files[course.filetype]["assignment"]
        shutil.copy(template_path, new_path)
        new_assignment = Assignment(new_path)
        return new_assignment

    def create_lecture(self, course: Course) -> Lecture:
        # TODO: add template
        lecture_path = course.next_lecture_path()
        main_file_path = course.main_file.path
        assert not lecture_path.exists() and lecture_path.parent.exists()
        lecture_path.touch()
        new_lecture = Lecture(lecture_path, main_file_path)
        course.add_lecture(new_lecture)
        # Update main file
        header, _, footer = get_header_footer(course.main_file.path)
        template_func = course.include_template()
        body = '\n'.join([template_func(lecture.name) for lecture in course.lectures]) + "\n"
        main_file_path.write_text(header + body + footer)
        return new_lecture


    def _load_assignments(self, course: Course, sort: bool=True) -> list[Assignment]:
        assignments, ignored = [], []
        suffix = {".typ", ".tex"}
        assignment_path = course.path / "assignments"
        if not assignment_path.exists() or not assignment_path.is_dir():
            return []

        for a in assignment_path.iterdir():
            if not a.is_file():
                continue
            if re.search(course.assignment_filename_pattern(), a.name):
                assignments.append(Assignment(a))
            elif a.suffix in suffix:
                ignored.append(a)
        if sort:
            assignments.sort(key=lambda a: a.number())
        return assignments

    def _load_lectures(self, course: Course, sort: bool = True) -> list[Lecture]:
        lectures, ignored = [], []
        suffix = {".typ", ".tex"} #TODO: FileType.Unsupported will cause error
        lecture_path = course.main_file.path.parent / "lectures"
        if not lecture_path.exists() or not lecture_path.is_dir():
            return []

        for l in lecture_path.iterdir():
            if not l.is_file():
                continue
            if re.search(course.lecture_filename_pattern(), l.name):
                lectures.append(Lecture(l, course.main_file.path))
            elif l.suffix in suffix:
                ignored.append(l)
        if sort:
            lectures.sort(key=lambda lec: lec.number())
        return lectures

