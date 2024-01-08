import lectures
from courses import Courses
import argparse
from pathlib import Path
from utils import load_json, dump_json

class CourseController:
    def __init__(self, project_config: dict):
       self.courses = Courses(project_config)

    def course(self, parser):
        if parser.create:
            if not parser.name:
                raise ValueError
            self.courses.create_course(parser.name)
            self._get_user_input(self.courses.courses[parser.name])

    def _get_user_input(self, course: Course):
        path = course.root / "course_info.json"
        dic = load_json(path)
        for key, val in dic:
            if val:
                continue
            print(f"Input value for key: {key}")
            val = input()
            dic[key] = val
        dump_json(path, dic)

    def write_json(self, path: str):
        with open(path, 'w') as f:
            json.dumps
    def lec(self, parser):
        pass
    def tex(self, parser):
        pass

