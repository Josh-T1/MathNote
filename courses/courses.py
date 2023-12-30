from lectures import Lectures
from config import Config
from pathlib import Path

# create script for adding course
# also create interface for removing courses



class Course():
    def __init__(self, path, config: dict) -> None:
        self.path = path
        self.name = path.stem
        self.config = config
        self._lectures = None

    @property
    def lectures(self):
        if not self.lectures:
            self._lectures = Lectures(self.path / 'lectures')
        return self._lectures

    def __eq__(self, other):
        if type(other) != type(self):
            return False
        return self.path == other.path

class Courses():
    def __init__(self, config: Config):
        self.config = config
        self.root = Path(config[""])
        self.courses = None

    def _find_courses(self):
        course_directories = [x for x in self.root.iterdir() if x.is_dir()] # how does iterdir work
        courses = [Course(course, self.config[f"{course.stem}"]) for course in course_directories]
        return sorted(courses, key=lambda c: c.name)

    def current(self):
        pass

