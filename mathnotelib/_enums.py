from enum import Enum, auto

class FileType(Enum):
    Typst = "Typst"
    LaTeX = "LaTeX"
    Unsupported = "Unsupported"


# TODO: delete?
class CourseSubdir(Enum):
    Assignment = auto()
    Lectures = auto()


class OutputFormat(Enum):
    PDF = "pdf"
    SVG = "svg"
