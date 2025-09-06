from enum import Enum, auto, IntEnum

class FileType(Enum):
    Typst = "Typst"
    LaTeX = "LaTeX"
    Unsupported = "Unsupported"

    @property
    def extension(self) -> str:
        return {
                FileType.LaTeX: ".tex",
                FileType.Typst: ".typ",
                FileType.Unsupported: ".txt"
                }[self]

    @classmethod
    def from_extension(cls, extension: str) -> 'FileType':
        """Create FileType from file extension (e.g., '.tex' -> FileType.LaTeX)"""
        if not extension.startswith("."):
            extension = "." + extension
        extension_map = {
            ".tex": cls.LaTeX,
            ".typ": cls.Typst,
        }
        return extension_map.get(extension, cls.Unsupported)



# TODO: delete?
class CourseSubdir(Enum):
    Assignment = auto()
    Lectures = auto()


class OutputFormat(Enum):
    PDF = "pdf"
    SVG = "svg"

    @property
    def extension(self) -> str:
        return {
                OutputFormat.PDF: ".pdf",
                OutputFormat.SVG: ".svg"
                }[self]

class LatexmkReturnCode(IntEnum):
    SUCCESS = 0
    BAD_ARGS = 10
    FILE_NOT_FOUND = 11
    COMPONENT_FAILURE = 12
    UNKNOWN_ERROR = -1  # fallback when not one of the above

