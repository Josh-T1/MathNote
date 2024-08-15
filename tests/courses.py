from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock, Mock
from ..course import courses as c
import datetime

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
        root_path, lec1_path, lec2_path = MagicMock(spec=Path), MagicMock(spec=Path), MagicMock(spec=Path)
        root_path.stem = "math-445"
        root_path.name = "math-445"
        mock_root_stat = Mock()
        mock_root_stat.st_mttime = 1234567890.0
        root_path.stat.return_value = mock_root_stat

        lec1_path.stem = "lec_01"
        lec1_path.name = "lec_01.tex"
        mock_lec1_stat = Mock()
        mock_lec1_stat.st_mttime = 1234577890.0
        lec1_path.stat.return_value = mock_root_stat

        lec2_path.stem = "lec_02"
        lec2_path.name = "lec_02.tex"
        mock_lec2_stat = Mock()
        mock_lec2_stat.st_mttime = 1234587890.0
        lec2_path.stat.return_value = mock_lec2_stat

        lecture1 = c.Lecture(lec1_path)
        lecture2 = c.Lecture(lec2_path)

        cls.course1 = c.Course(root_path)
        cls.course1._lectures = [lecture1, lecture2]
        cls.course1._course_info = {"weekdays": ["Monday", "Wednesday", "Friday"],
                             "start-time": "3:00",
                             "end-time": "3:50",
                             "start-date": "2020-09-12",
                             "end-date": "2020-09-12"}
        now = datetime.datetime.now()
        start_date = now.date() - datetime.timedelta(days=5)
        end_date = now.date() + datetime.timedelta(days=5)
        start_time = now + datetime.timedelta(minutes=5)
        end_time = now + datetime.timedelta(minutes=55)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        start_time_str = start_time.strftime("%H:%M")
        end_time_str = end_time.strftime("%H:%M")
        day_map = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thusday",
                 4: "Friday", 5: "Saturday", 6: "Sunday"}
        cls.course2 = c.Course(root_path)
        cls.course2._lectures = [lecture1, lecture2]
        cls.course2._course_info = {"weekdays": [day_map[now.weekday()]],
                             "start-time": start_time_str,
                             "end-time": end_time_str,
                             "start-date": start_date_str,
                             "end-date": end_date_str}

    def test_lectures(self):
        self.assertEqual(len(self.course1.lectures), 2)

    def test_this_semester(self):
        self.assertFalse(self.course1.this_semester())
        self.assertTrue(self.course2.this_semester())

    def test_start_time(self):
        self.assertEqual(self.course1.start_time(), datetime.datetime.strptime("03:00", "%H:%M"))

    def test_end_time(self):
        self.assertEqual(self.course1.end_time(), datetime.datetime.strptime("03:50", "%H:%M"))

    def test_days(self):
        self.assertListEqual(self.course1.days(), ["Monday", "Wednesday", "Friday"])
    @patch()
    def test_new_lecture(self):
        pass


if __name__ == "__main__":
    unittest.main()
