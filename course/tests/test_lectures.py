from course.lectures import Lecture, Lectures
from pathlib import Path

PATH = Path("/Users/test/lec_03.tex")

def test_lecture_number():
    lecture = Lecture(PATH)
    assert lecture.number == 3


