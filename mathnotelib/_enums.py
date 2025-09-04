from enum import Enum, auto, IntEnum

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

class LatexmkReturnCode(IntEnum):
    SUCCESS = 0
    BAD_ARGS = 10
    FILE_NOT_FOUND = 11
    COMPONENT_FAILURE = 12
    UNKNOWN_ERROR = -1  # fallback when not one of the above

