import shutil
from datetime import datetime
import subprocess
from pathlib import Path
from config.config import Config
from typing import Union
from dataclasses import dataclass

config = Config()

def number2filename(n):
    return 'lec_{0:02d}.tex'.format(n)

def filename2number(s):
    return int(str(s).replace('.tex', '').replace('lec_', ''))

@dataclass
class Lecture():
    file_path: Path

    def __post__init__(self):
        self.number = int(self.file_path.stem)

class Lectures():
    def __init__(self, path: Path):
        self.root = path
        self.lecture_path = self.root / 'lectures'
        self.master_file = self.root / 'main_file.tex'
        self.files = self.read_files()

    def read_files(self) -> list[Lecture]:
        files = self.root.glob('lec_*.tex')
        return sorted((Lecture(f) for f in files), key=lambda l: l.number)

    def parse_lecture_range(self, string: str) -> int:
        if string.isdigit():
            return int(string)
        elif string == "last":
            return self.files[-1].number
        elif string == 'prev':
            return self.files[-1].number -1
        else:
            return 0

    def parse_range_string(self, arg: str) -> list[int]:
        all_numbers = [lecture.number for lecture in self.files]
        if 'all' in arg:
            return all_numbers
        if '-' in arg:
            start, end = self.parse_lecture_range(arg.split('-')[0]), self.parse_lecture_range(arg.split('-')[2])
            return [num for num in all_numbers if start<= num <= end]
            #return list(set(all_numbers) & set(range(start, end + 1)))
        return [self.parse_lecture_range(arg)]

    @staticmethod
    def get_header_footer(filepath: Path) -> tuple[str, str]:
        part = "header"
        header = ''
        footer = ''
        with filepath.open() as f:
            for line in f:
                if 'end lectures' in line:
                    part = 'footer'

                if part == 'header':
                    header += line

                if part == 'footer':
                    footer += line

        return (header, footer)

    def update_lectures_in_master(self, lecture_nums: list[int]) -> None: # wtf is r
        header, footer = self.get_header_footer(self.master_file)
        body = ''.join(
                ' ' * 4 + r'\input{' + number2filename(number) + '}\n' for number in lecture_nums
                )
        self.master_file.write_text(header + body + footer)

    def new_lecture(self):
        if len(self.files) != 0:
            new_lecture_number = self.files[-1].number + 1
        else:
            new_lecture_number = 1

        new_lecture_path = self.root / number2filename(new_lecture_number)
        shutil.copyfile(config[LECTURE_TEMPLATE], new_lecture_path)
        #new_lecture_path.touch() # Copy file template instead of touch?
        new_lecture_path.write_text(f'\\begin{{document}}\n\\subsection*{{Lecture{new_lecture_number}}}\n\\end{{document}}\n')

        if new_lecture_number == 1:
            self.update_lectures_in_master([1]) # why the fuck is there a box around 1
        else:
            self.update_lectures_in_master([new_lecture_number -1, new_lecture_number])

        l = Lecture(new_lecture_path, self.course)
        return l

    def complile_main(self):
        result = subprocess.run(
                ['latexmk', '-f', '-interaction=nonstopmode', str(self.master_file)],
                stdout = subprocess.DEVNULL,
                stderr = subprocess.DEVNULL,
                cwd=str(self.root)
                )
        return result.returncode
