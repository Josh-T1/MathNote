from __future__ import annotations
import tempfile
from pathlib import Path
from typing import Literal

from PyQt6.QtCore import QFileSystemWatcher, QModelIndex, QObject, QProcess, QTimer, Qt
from PyQt6.QtGui import QStandardItem
from PyQt6.QtWidgets import QMainWindow

from . import constants
from .navbar import CourseNavBar, NavBarContainer, NotesNavBar
from .dialog import NewCourseDialog, NewNoteDialog, NameDialog, show_error_dialog
from .viewer import TabbedSvgViewer
from .ui_components import confirm_delete
from ..models import Category, Course, SourceFile, Note
from ..utils import rendered_sorted_key
from ..services import CompileOptions, compile_source, NotesRepository, CourseRepository
from ..config import CONFIG
from .._enums import OutputFormat
from ..exceptions import CompilationError, NoItemSelected, NoteExistsError, CategoryExistsError, InvalidNameError, NoteExistsError, CourseExistsError


def with_error_dialog(func):
    def wrapper(self: NoteController | CourseController, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except (NoteExistsError, CourseExistsError, InvalidNameError, CategoryExistsError) as e:
            show_error_dialog(self.window, str(e))
        except Exception as e:
            show_error_dialog(self.window, f"Unexpected error: {e}")
    return wrapper


class NoteController(QObject):
    def __init__(self, window: QMainWindow, navbar: NotesNavBar, viewer: TabbedSvgViewer):
        self.window = window
        self.navbar = navbar
        self.viewer = viewer
        self.notes_repo = NotesRepository(CONFIG)
        self._init_tree()
        self.connect_handlers()

    def connect_handlers(self):
        self.navbar.new_note.connect(lambda: self.handle_create("Note"))
        self.navbar.file_opened.connect(lambda f: self.handle_file_opened(f))
        self.navbar.new_category.connect(lambda: self.handle_create("Category"))
        self.navbar.delete.connect(lambda: self.handle_delete())
        self.navbar.rename.connect(lambda: self.handle_rename())
        self.navbar.load_item.connect(lambda item, cat: self.handle_load_item(item, cat))

    def handle_load_item(self, item: QStandardItem, cat: Category):
        item.removeRows(0, item.rowCount())
        subcategories = self.notes_repo.get_sub_categories(cat)
        for sub_cat in subcategories:
            item.appendRow(self.navbar._build_cat_item(sub_cat))

        for note in cat.notes:
            item.appendRow(self.navbar._build_file_item(note))

        if len(cat.notes) + len(subcategories) > 0:
            item.setData(True, constants.LOADED_ROLE)

    def _init_tree(self):
        self.navbar.root_item().setData(self.notes_repo.root_category, constants.DIR_ROLE)
        sub_categories = self.notes_repo.get_sub_categories(self.notes_repo.root_category)
        for child in sub_categories:
            self.navbar.root_item().appendRow(self.navbar._build_cat_item(child))
        for note in self.notes_repo.root_category.notes:
            self.navbar.root_item().appendRow(self.navbar._build_file_item(note))

    @with_error_dialog
    def handle_rename(self):
        item, idx = self.navbar._get_item_and_index()
        if item is None:
            return
        parent = item.parent() or self.navbar.root_item()
        dialog = NameDialog()
        if not dialog.exec():
            return
        name = dialog.get_data()

        if (file := item.data(constants.FILE_ROLE)) is not None:
            assert isinstance(file, Note)
            renamed_obj = self.notes_repo.rename_note(file, name)
            target_category = None if renamed_obj is None else renamed_obj.category

        elif (cat := item.data(constants.DIR_ROLE)) is not None:
            assert isinstance(cat, Category)
            renamed_obj = self.notes_repo.rename_cat(cat, name)
            target_category = None if renamed_obj is None else renamed_obj.parent or self.notes_repo.root_category
        else:
            return
        if target_category is not None:
            self.handle_load_item(parent, target_category)

    def _delete_item(self, item: Note | Category, idx: QModelIndex) -> bool:
        delete = confirm_delete(self.window, item)
        if not delete:
            return False
        del_map = {
                Category: self.notes_repo.delete_category,
                Note: self.notes_repo.delete_note
                }
        del_map[type(item)](item)
        self.navbar.model.removeRow(idx.row(), idx.parent())
        return True

    @with_error_dialog
    def handle_delete(self):
        item, idx = self.navbar._get_item_and_index()
        if item is None or idx is None:
            raise NoItemSelected("Cannot delete, no item selected")
        parent = item.parent() or self.navbar.root_item()

        if (dir := item.data(constants.DIR_ROLE)) is not None:
            assert isinstance(dir, Category)
            delete = self._delete_item(dir, idx)

        elif (file := item.data(constants.FILE_ROLE)) is not None:
            assert isinstance(file, Note)
            delete = self._delete_item(file, idx)
        else:
            return
        if parent is not None and parent.rowCount() == 0 and delete: # TODO why row count?
            self.navbar.tree.collapse(parent.index())
            parent.setData(False, constants.LOADED_ROLE)

    @with_error_dialog
    def handle_create(self, item_type: Literal["Note"] | Literal["Category"]):
        item, idx = self.navbar._get_item_and_index()
        # Given item we determine parent_item in tree (depends on isExpanded()) and set cat to be parent category
        if item is None or idx is None:
            parent_item = self.navbar.root_item()
            cat = self.notes_repo.root_category

        elif (note := item.data(constants.FILE_ROLE)) is not None:
            assert isinstance(note, Note)
            cat = note.category
            parent_item = item.parent() or self.navbar.root_item()

        elif (cat := item.data(constants.DIR_ROLE)) is not None:
            assert isinstance(cat, Category)
            # If tree expanded around category item => parent in tree is selected item
            if self.navbar.tree.isExpanded(idx):
                cat: Category = item.data(constants.DIR_ROLE)
                parent_item = item
            # If tree not expanded => parent in tree is selected items parent
            else:
                parent_item = item.parent() or self.navbar.root_item()
                cat: Category = parent_item.data(constants.DIR_ROLE)
        else:
            return

        if item_type == "Note":
            dialog = NewNoteDialog()
            if not dialog.exec(): return
            name, ftype = dialog.get_data()
            note = self.notes_repo.create_note(name, cat, ftype)
            res_item = self.navbar._build_file_item(note)

            self.viewer.add_svg_tab(focus=True)
            self.navbar.file_opened.emit(note)
            self.navbar.tree.setCurrentIndex(res_item.index())
        else:
            dialog = NameDialog()
            if not dialog.exec(): return
            name = dialog.get_data()
            res = self.notes_repo.create_category(name, cat)
            res_item = self.navbar._build_cat_item(res)

        if parent_item is not None: # Should be impossible
            parent_item.appendRow(res_item)
            self.navbar.tree.expand(parent_item.index())

    @with_error_dialog
    def handle_file_opened(self, file: SourceFile):
        # No tabs => Add tab
        tmpdir = tempfile.TemporaryDirectory()
        tmpdir_path = Path(tmpdir.name)

        options = CompileOptions(file.path, OutputFormat.SVG, multi_page=True)
        options.set_output_dir(tmpdir_path)
        options.set_output_file_stem(constants.OUTPUT_FILE_STEM)

        if isinstance(file, Note):
            file_name = file.name
        # handle course. Example path: CourseName/main/main.ext
        else:
            file_name = file.path.parent.parent.stem
        compilation_res = compile_source(file, options)
        svg_files = sorted(tmpdir_path.glob(f"{constants.OUTPUT_FILE_STEM}*.svg"), key=rendered_sorted_key)
        if len(svg_files) == 0:
            raise CompilationError(compilation_res[1])
        self._update_svg(svg_files, tmpdir, file_name)

    def _update_svg(self, path: Path | list[Path], tmpdir: tempfile.TemporaryDirectory, name: str | None=None):
        paths = path if isinstance(path, list) else [path]
        if all(p.exists() for p in paths):
            self.viewer.load_current_viewer([str(p) for p in paths], tmpdir=tmpdir, name=name)


class CourseController(QObject):
    def __init__(self, window: QMainWindow, navbar: CourseNavBar, viewer: TabbedSvgViewer):
        self.window = window
        self.navbar = navbar
        self.viewer = viewer
        self.course_repo = CourseRepository(CONFIG)
        self.init_tree()
        self.connect_handlers()

    def add_course(self, course: Course):
        course_item = QStandardItem(course.name)
        course_item.setFlags(course_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        course_item.setData(course, constants.COURSE_CONTAINER_ROLE)
        self.navbar.root_item().appendRow(course_item)
        main_item = QStandardItem("main")
        main_item.setFlags(main_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        main_item.setData(course.main_file, constants.FILE_ROLE)
        course_item.appendRow(main_item)

        for dir_name in Course.source_file_directories:
            if not (course.path / dir_name).is_dir():
                continue
            dir_item = QStandardItem(dir_name.name)
            dir_item.setData(True, constants.COURSE_DIR)
            course_item.appendRow(dir_item)
            files = getattr(course, dir_name.name, [])
            for source_file in files:
                assert isinstance(source_file, SourceFile)
                item = self.navbar._build_file_item(source_file)
                dir_item.appendRow(item)

    def init_tree(self):
        for course in self.course_repo.courses().values():
            self.add_course(course)

    def connect_handlers(self):
        self.navbar.file_opened.connect(lambda f: self.handle_file_opened(f))
        self.navbar.delete.connect(lambda: self.handle_delete())
        self.navbar.new_course.connect(lambda: self.handle_new_course())
        self.navbar.new_assignment.connect(lambda: self.handle_new_course())
        self.navbar.new_lecture.connect(lambda: self.handle_new_course())

    @with_error_dialog
    def handle_new_course(self):
        dialog = NewCourseDialog()
        if not dialog.exec():
            return
        name, ftype, start_t, end_t, weekdays, start_d, end_d = dialog.get_data()
        course = self.course_repo.create_course(name, ftype, start_t, end_t, weekdays, start_d, end_d)
        if course is not None:
            self.add_course(course)

    def handle_rename(self):
        pass
    def handle_new_lecture(self):
        pass
    def handle_new_assignment(self):
        pass

    @with_error_dialog
    def handle_delete(self):
        # file => course or note.
        item, idx = self.navbar._get_item_and_index()
        if item is None or idx is None:
            raise NoItemSelected("Cannot delete, no item selected")
        parent = item.parent() or self.navbar.root_item()
        # Test
        if item.data(constants.DIR_ROLE) is not None:
            delete = False
            parent = item.parent()
            while parent is not None:
                if (course := parent.data(constants.COURSE_CONTAINER_ROLE)) is not None:
                    delete = self._delete_course(course, parent.index())
                    break
                parent = parent.parent()
#            delete = self._delete_category(dir, idx)
        elif (course := item.data(constants.COURSE_CONTAINER_ROLE)) is not None:
            delete = self._delete_course(course, idx)
        elif (file := item.data(constants.FILE_ROLE)) is not None:
            delete = self._delete_file(file, idx)
        else:
            return
        if parent is not None and parent.rowCount() == 0 and delete:
            self.navbar.tree.collapse(parent.index())
            parent.setData(False, constants.LOADED_ROLE)

    def _delete_course(self, course: Course, idx: QModelIndex) -> bool:
        delete = confirm_delete(self.window, course)
        if not delete:
            return False
        self.course_repo.delete_course(course)
        self.navbar.model.removeRow(idx.row(), idx.parent())
        return True

    @with_error_dialog
    def handle_file_opened(self, file: SourceFile):
        # No tabs => Add tab
        tmpdir = tempfile.TemporaryDirectory()
        tmpdir_path = Path(tmpdir.name)

        options = CompileOptions(file.path, OutputFormat.SVG, multi_page=True)
        options.set_output_dir(tmpdir_path)
        options.set_output_file_stem(constants.OUTPUT_FILE_STEM)
        # This does not work
        file_name = file.path.parent.parent.stem
        compilation_res = compile_source(file, options)
        svg_files = sorted(tmpdir_path.glob(f"{constants.OUTPUT_FILE_STEM}*.svg"), key=rendered_sorted_key)
        if len(svg_files) == 0:
            raise CompilationError(compilation_res[1])
        self._update_svg(svg_files, tmpdir, file_name)

    def _update_svg(self, path: Path | list[Path], tmpdir: tempfile.TemporaryDirectory, name: str | None=None):
        paths = path if isinstance(path, list) else [path]
        if all(p.exists() for p in paths):
            self.viewer.load_current_viewer([str(p) for p in paths], tmpdir=tmpdir, name=name)

    # TODO: implement
    def _delete_file(self, file: SourceFile, idx: QModelIndex) -> bool:
        delete = confirm_delete(self.window, file)
        if not delete:
            return False
        # TODO, handle file delete within course
#        if isinstance(file, CourseBoundSourceFile):
#            self.notes_manager.del_note(file)
#            self.navbar.model.removeRow(idx.row(), idx.parent())
#            return True
        return False

class LiveTypstController:
    def __init__(self, navbar: NavBarContainer, viewer: TabbedSvgViewer):
        self.navbar = navbar
        self.viewer = viewer
        self.watcher = QFileSystemWatcher()
        self.watcher.addPath(constants.TYP_FILE_LIVE)

        self.process = None

        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(lambda: self.compile_typst(constants.TYP_FILE_LIVE))

    def connect_handlers(self):
        self.navbar.preview.connect(lambda: self.handle_preview())

    def handle_preview(self):
        self.compile_typst(constants.TYP_FILE_LIVE)

    def on_typ_changed(self):
        if not self._debounce_timer.isActive():
            self._debounce_timer.start(200)
#
    def compile_typst(self, path: str):
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()  # Stop any ongoing compilation

        self.process = QProcess()
        self.process.finished.connect(lambda : self._update_svg())
        self.process.start("typst", ["compile", path, "--format", "svg"])


    def _update_svg(self):
        svg_path = constants.TYP_FILE_LIVE.replace(".typ", ".svg")
        self.viewer.load_current_viewer(svg_path)

