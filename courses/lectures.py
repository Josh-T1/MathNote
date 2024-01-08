import subprocess
from pathlib import Path


def number2filename(n):
    return 'lec_{0:02d}.tex'.format(n)

def filename2number(s):
    return int(str(s).replace('.tex', '').replace('lec_', ''))

class Lecture():
    """ Stores content of individual lecture and contains methods for parsing file to get lecture properties such as 'theorems' or 'definitions'
    TODO: add parsing methods. theorems, statements, definitions. How do I determine relevent lectures by unit?
    """
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path

    @property
    def number(self):
        # ** DOES this Work
        return int(self.file_path.stem) # this definitly does not work

    @property
    def last_edit(self) -> float:
        """ Returns most recent edit in seconds """
        return self.file_path.stat().st_mtime

class Lectures():
    def __init__(self, path: Path):
        self.root = path
        self.lecture_path = self.root / 'lectures'
        self.master_file = self.root / 'main.tex'
        self._lectures = []

    @property
    def lectures(self) -> list[Lecture]:
        if self._lectures:
            return self._lectures
        files = self.root.glob('lec_*.tex')
        self._lectures = sorted((Lecture(f) for f in files), key=lambda l: l.number)
        return self._lectures

    def parse_lecture_range(self, string: str) -> int:
        if string.isdigit():
            return int(string)
        elif string == "last":
            return self.lectures[-1].number
        elif string == 'prev':
            return self.lectures[-1].number -1
        else:
            return 0

    def parse_range_string(self, arg: str) -> list[int]:
        all_numbers = [lecture.number for lecture in self.lectures]
        if 'all' in arg:
            return all_numbers
        if '-' in arg:
            start, end = self.parse_lecture_range(arg.split('-')[0]), self.parse_lecture_range(arg.split('-')[2])
            return [num for num in all_numbers if start<= num <= end]
            #return list(set(all_numbers) & set(range(start, end + 1)))
        return [self.parse_lecture_range(arg)]

    @staticmethod
    def get_header_footer(filepath: Path) -> tuple[str, str]:
        """ Copy header and footer main.tex """
        part = "header"
        header, footer = '', ''

        with filepath.open() as f:
            for line in f:
                if 'end lectures' in line:
                    part = 'footer'

                if part == 'header':
                    header += line

                if part == 'footer':
                    footer += line

                if "start lectures" in line:
                    part = "body"

        return (header, footer)

    def update_lectures_in_master(self, lecture_nums: list[int]) -> None: # wtf is r
        header, footer = self.get_header_footer(self.master_file)
        body = ''.join(' ' * 4 + r'\input{' + number2filename(number) + '}\n' for number in lecture_nums)
        self.master_file.write_text(header + body + footer)

    def new_lecture(self):
        new_lecture_number = 1 if not self.lectures else self.lectures[-1].number +1

        new_lecture_path = self.root / number2filename(new_lecture_number)
        new_lecture_path.touch() # Copy file template instead of touch?
        new_lecture_path.write_text(f'\\{{lecture{{{new_lecture_number}}}}}\n')

        self.update_lectures_in_master([new_lecture_number]) # [new_lecture_number-1, new_lecture_number] when num!=1,  why?

        new_lecture = Lecture(new_lecture_path)
        self._lectures.append(new_lecture)
        return new_lecture

    def complile_main(self):
        result = subprocess.run(
                ['latexmk', '-f', '-interaction=nonstopmode', str(self.master_file)],
                stdout = subprocess.DEVNULL,
                stderr = subprocess.DEVNULL,
                cwd=str(self.root)
                )
        return result.returncode
