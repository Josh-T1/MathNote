import tempfile
from pathlib import Path
import logging

from PyQt6.QtCore import QModelIndex, QObject, Qt
from PyQt6.QtGui import QStandardItem
from PyQt6.QtWidgets import QMainWindow

from .ui_utils import with_error_dialog
from ..constants import DIR_ROLE, COURSE_CONTAINER_ROLE, COURSE_DIR, FILE_ROLE, LOADED_ROLE, OUTPUT_FILE_STEM
from ..navbar import CourseNavbar
from ..dialog import NewCourseDialog, confirm_delete
from ..file_viewer import TabbedSvgViewer
from ...models import Course, SourceFile
from ...services import CompileOptions, compile_source, CourseRepository
from ...config import CONFIG
from ...enums import OutputFormat
from ...exceptions import CompilationError, NoItemSelected




logger = logging.getLogger(__name__)

class CourseController(QObject):
    def __init__(self, window: QMainWindow, navbar: CourseNavbar, viewer: TabbedSvgViewer):
        super().__init__()
        self.window = window
        self.navbar = navbar
        self.viewer = viewer
        self.course_repo = CourseRepository(CONFIG)
        self._populate_view()
        self.connect_handlers()

    def add_course(self, course: Course):
        course_item = QStandardItem(course.name)
        course_item.setFlags(course_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        course_item.setData(course, COURSE_CONTAINER_ROLE)
        self.navbar.root_item().appendRow(course_item)
        main_item = QStandardItem("main")
        main_item.setFlags(main_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        main_item.setData(course.main_file, FILE_ROLE)
        course_item.appendRow(main_item)

        for dir in Course.source_file_directories:
            if not (course.path / dir).is_dir():
                continue
            dir_item = QStandardItem(dir.name)
            dir_item.setData(dir.name, COURSE_DIR)
            dir_item.setFlags(main_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            course_item.appendRow(dir_item)
            files = getattr(course, dir.name, [])
            for source_file in files:
                assert isinstance(source_file, SourceFile), f"Course file has unexpected type '{type(source_file)}', expected 'SourceFile'"
                item = self.navbar._build_file_item(source_file)
                dir_item.appendRow(item)

    def _populate_view(self):
        for course in self.course_repo.courses(sort=True).values():
            self.add_course(course)

    def connect_handlers(self):
        self.navbar.file_opened.connect(lambda f: self.handle_file_opened(f))
        self.navbar.delete.connect(lambda: self.handle_delete())
        self.navbar.new_course.connect(lambda: self.handle_new_course())
        self.navbar.new_assignment.connect(lambda: self.handle_new_assignment())
        self.navbar.new_lecture.connect(lambda: self.handle_new_lecture())

    @with_error_dialog
    def handle_new_course(self):
        dialog = NewCourseDialog()
        if not dialog.exec():
            return
        name, ftype, start_t, end_t, weekdays, start_d, end_d = dialog.get_data()
        course = self.course_repo.create_course(name, ftype, start_t, end_t, weekdays, start_d, end_d)
        if course is not None:
            self.add_course(course)

    # TODO
    @with_error_dialog
    def handle_rename(self):
        pass

    def _get_course(self, item: QStandardItem) -> tuple[Course, QStandardItem]:
        parent = item
        while parent:
            if (course := parent.data(COURSE_CONTAINER_ROLE)) is not None:
                assert isinstance(course, Course), f"Tree item has unexpected type '{type(course)}', expected 'Course'"
                return course, parent
            parent = parent.parent()
        raise Exception("Unable to determine course")

    def _search_tree(self, item: QStandardItem, name: str) -> QStandardItem | None:
        if item.data(COURSE_DIR) == name:
            return item
        for row in range(item.rowCount()):
            child = item.child(row)
            if child is None:
                continue
            if child.data(COURSE_DIR) == name:
                return child
            self._search_tree(child, name)
        return None


    @with_error_dialog
    def handle_new_lecture(self):
        item, _ = self.navbar._get_item_and_index()
        if item is None:
            raise NoItemSelected("No course selected")

        course, course_item = self._get_course(item)
        new_lecture = self.course_repo.create_lecture(course)
        lecture_item = self.navbar._build_file_item(new_lecture)
        parent_item = self._search_tree(course_item, "lectures")

        if parent_item is None:
            raise Exception("Could not find parent in tree view from current selection")
        parent_item.appendRow(lecture_item)

        self.navbar.tree.expand(parent_item.index())

    @with_error_dialog
    def handle_new_assignment(self):
        item, _ = self.navbar._get_item_and_index()
        if item is None:
            raise NoItemSelected("No course selected")

        course, course_item = self._get_course(item)
        new_assignment = self.course_repo.create_assignment(course)
        assignment_item = self.navbar._build_file_item(new_assignment)

        parent_item = self._search_tree(course_item, "assignments")
        if parent_item is None:
            raise Exception("Could not find parent in tree view from current selection")
        parent_item.appendRow(assignment_item)

        self.navbar.tree.expand(parent_item.index())


    @with_error_dialog
    def handle_delete(self):
        # TODO: prevent protected directories from begin deleted
        item, idx = self.navbar._get_item_and_index()
        if item is None or idx is None:
            raise NoItemSelected("Cannot delete, no item selected")
        parent = item.parent() or self.navbar.root_item()
        # Test
        if item.data(DIR_ROLE) is not None:
            delete = False
            parent = item.parent()
            while parent is not None:
                if (course := parent.data(COURSE_CONTAINER_ROLE)) is not None:
                    delete = self._delete_course(course, parent.index())
                    break
                parent = parent.parent()
#            delete = self._delete_category(dir, idx)
        elif (course := item.data(COURSE_CONTAINER_ROLE)) is not None:
            delete = self._delete_course(course, idx)
        elif (file := item.data(FILE_ROLE)) is not None:
            delete = self._delete_file(file, idx)
        else:
            return
        if parent is not None and parent.rowCount() == 0 and delete:
            self.navbar.tree.collapse(parent.index())
            parent.setData(False, LOADED_ROLE)

    def _delete_course(self, course: Course, idx: QModelIndex) -> bool:
        delete = confirm_delete(self.window, course.name)
        if not delete:
            return False
        self.course_repo.delete_course(course)
        self.navbar.model.removeRow(idx.row(), idx.parent())
        return True

    @with_error_dialog
    def handle_file_opened(self, file: SourceFile):
        tmpdir = tempfile.TemporaryDirectory()
        tmpdir_path = Path(tmpdir.name)

        options = CompileOptions(file.path, OutputFormat.SVG, multi_page=True)
        options.set_output_dir(tmpdir_path)
        options.set_output_file_stem(OUTPUT_FILE_STEM)

        compilation_res = compile_source(file, options)
        svg_files = sorted(tmpdir_path.glob(f"{OUTPUT_FILE_STEM}*.svg"), key=rendered_sorted_key)
        if len(svg_files) == 0:
            raise CompilationError(compilation_res[1])
        self._update_svg(svg_files, tmpdir, file)

    def _update_svg(self, path: Path | list[Path], tmpdir: tempfile.TemporaryDirectory, source: SourceFile | None=None):
        paths = path if isinstance(path, list) else [path]
        if all(p.exists() for p in paths):
            self.viewer.load_current_viewer([str(p) for p in paths], tmpdir=tmpdir, source=source)

    # TODO: implement
    def _delete_file(self, file: SourceFile, idx: QModelIndex) -> bool:
        delete = confirm_delete(self.window, file.name)
        if not delete:
            return False
        # TODO, handle file delete within course
#        if isinstance(file, CourseBoundSourceFile):
#            self.notes_manager.del_note(file)
#            self.navbar.model.removeRow(idx.row(), idx.parent())
#            return True
        return False

