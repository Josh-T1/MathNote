from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock, Mock
from ..course import courses as c

class TestNumber2Filename(unittest.TestCase):
    def setUp(self):
        self.num = 4

    def test(self):
        lec_name = c.number2filename(self.num)
        self.assertEqual(lec_name, f"lec_0{self.num}.tex")

class TestFilename2Number(unittest.TestCase):
    def setUp(self):
        self.filename = "lec_03.tex"
        self.filename2 = "lec_33.tex"

    def test(self):
        num = c.filename2number(self.filename)
        num2 = c.filename2number(self.filename2)
        self.assertEqual(num, 3)
        self.assertEqual(num2, 33)


class TestLecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lecture = c.Lecture(Path("/Users/user/school/lec_03.tex"))
        cls.lecture2 = c.Lecture(Path("/Users/user/school/lec_33.tex"))

    def test_number(self):
        self.assertEqual(self.lecture.number(), 3)
        self.assertEqual(self.lecture2.number(), 33)

    def test_name(self):
        self.assertEqual(self.lecture.name(), "lec_03.tex")
        self.assertEqual(self.lecture2.name(), "lec_33.tex")



class TestCourse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = Path("/Users/user/notes/math-445")
        cls.course = c.Course(cls.path)

    def setUp(self):
        self.mock_lecture1 = Mock()
        self.mock_lecture2 = Mock()

    @patch.object(c.Course, 'lectures')
    def test_lectures(self, mock_lectures):
        mock_lectures.return_value = [self.mock_lecture1, self.mock_lecture2]



if __name__ == "__main__":
    unittest.main()
