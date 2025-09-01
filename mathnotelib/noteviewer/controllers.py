import tempfile
from pathlib import Path
from typing import Literal

from PyQt6.QtCore import QFileSystemWatcher, QModelIndex, QObject, Qt
from PyQt6.QtGui import QStandardItem
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QWidget

from . import constants
from .navbar import CourseNavBar, NewCourseDialog, NewNoteDialog, NameDialog, NotesNavBar
from .viewer import TabbedSvgViewer
from ..models import Category, Course, SourceFile, Note
from ..utils import rendered_sorted_key
from ..services import CompileOptions, compile_source, NotesRepository, CourseRepository
from ..config import CONFIG
from .._enums import OutputFormat


def confirm_delete(window: QWidget, item: SourceFile | Course | Category) -> bool:
    """
    Show a confirmation dialog before deleting.

    Args:
        parent: Parent widget (e.g. main window).
        name: Name of the object to delete.
        kind: Type of object (e.g. "note", "course", "file").

    Returns:
        True if user confirmed, False otherwise.
    """
    msg = QMessageBox(window)
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setWindowTitle(f"Delete {item.name}")
    msg.setText(f"Are you sure you want to delete the {type(item).__name__} '{item.name}'?")
    msg.setInformativeText("This action cannot be undone.")
    msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
    msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
    result = msg.exec()
    return result == QMessageBox.StandardButton.Yes


class NoteController(QObject):
    def __init__(self, window: QMainWindow, navbar: NotesNavBar, viewer: TabbedSvgViewer):
        self.window = window
        self.navbar = navbar
        self.viewer = viewer
        self.notes_repo = NotesRepository(CONFIG.root_path / "Notes")

        self.handle_init_tree()
        self.connect_handlers()

    def connect_handlers(self):
        self.navbar.new_note.connect(lambda: self.handle_new_note())
        self.navbar.file_opened.connect(lambda f: self.handle_file_opened(f))
        self.navbar.new_category.connect(lambda: self.handle_new_category())
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

    def handle_init_tree(self):
        sub_categories = self.notes_repo.get_sub_categories(self.notes_repo.root_category)
        for child in sub_categories:
            self.navbar.root_item().appendRow(self.navbar._build_cat_item(child))
        for note in self.notes_repo.root_category.notes:
            self.navbar.root_item().appendRow(self.navbar._build_file_item(note))

    def handle_rename(self):
        item, idx = self._get_item_and_index()
        if item is None:
            return
        parent = item.parent() or self.navbar.root_item()
        assert parent is not None
        dialog = NameDialog()
        if not dialog.exec():
            return
        name = dialog.get_data()
        if (file := item.data(constants.FILE_ROLE)) is not None:
            self.notes_repo.rename_note(file, name)
            self.handle_load_item(parent, file.category)
        elif (cat := item.data(constants.DIR_ROLE)) is not None:
            self.notes_repo.rename_cat(cat, name)
            self.handle_load_item(parent, cat.parent)

    def handle_delete(self):
        # file => course or note.
        item, idx = self._get_item_and_index()
        if item is None or idx is None:
            return
        parent = item.parent() or self.navbar.root_item()
        if (dir := item.data(constants.DIR_ROLE)) is not None:
            delete = self._delete_category(dir, idx)
        elif (file := item.data(constants.FILE_ROLE)) is not None:
            delete = self._delete_file(file, idx)
        else:
            return
        if parent is not None and parent.rowCount() == 0 and delete:
            self.navbar.tree.collapse(parent.index())
            parent.setData(False, constants.LOADED_ROLE)

    def handle_new_category(self):
        item, idx = self._get_item_and_index()
        if item is None or idx is None:
            parent_item = self.navbar.root_item()
            cat = self.notes_repo.root_category

        elif isinstance(item.data(constants.FILE_ROLE), Note):
            note: Note = item.data(constants.FILE_ROLE)
            cat = note.category
            parent_item = item.parent() or self.navbar.root_item()

        elif isinstance(item.data(constants.DIR_ROLE), Category):
            if self.navbar.tree.isExpanded(idx):
                cat: Category = item.data(constants.DIR_ROLE)
                parent_item = item
            else:
                parent_item = item.parent() or self.navbar.root_item()
                cat: Category = parent_item.data(constants.DIR_ROLE)
        else:
            return
        dialog = NameDialog("New Category")
        if not dialog.exec():
            return
        name = dialog.get_data()
        res = self.notes_repo.create_category(name, cat)
        if res is None:
            return
        if parent_item is not None: # Should be impossible
            parent_item.appendRow(self.navbar._build_cat_item(res))
            self.navbar.tree.expand(parent_item.index())

    def handle_new_note(self):
        item, idx = self._get_item_and_index()
        if idx is None or item is None:
            self._add_to_tree(self.navbar.root_item(), self.notes_repo.root_category, load_viewer=True)

        elif (obj := item.data(constants.FILE_ROLE)) is not None:
            parent = item.parent() or self.navbar.root_item()
            self._add_to_tree(parent, obj.category, load_viewer=True)
            self.navbar.tree.expand(parent.index())

        elif (obj := item.data(constants.DIR_ROLE)) is not None:
            if self.navbar.tree.isExpanded(idx):
                self._add_to_tree(item, obj, load_viewer=True)
                self.navbar.tree.expand(idx)
            else:
                parent_item = item.parent() or self.navbar.root_item()
                parent = parent_item.data(constants.DIR_ROLE)
                self._add_to_tree(parent_item, obj.parent)

                self.navbar.tree.expand(parent_item.index())

    def _add_to_tree(self, parent: QStandardItem, cat: Category | None, load_viewer: bool = False) -> Literal[0] | Literal[1]:
        # get params, creates note, adds new tab and tries to load new file
        cat = cat if cat is not None else self.notes_repo.root_category
        dialog = NewNoteDialog()
        if dialog.exec():
            name, ftype = dialog.get_data()
            note = self.notes_repo.create_note(name, cat, ftype)
            if note is None:
                return 1
            if parent is None:
                return
            tree_item = self.navbar._build_file_item(note)
            parent.appendRow(tree_item) # kind of unessary
            # add tab, focus tab, load viewer
            if load_viewer:
                self.viewer.add_svg_tab(focus=True)
                self.navbar.file_opened.emit(note)
                self.navbar.tree.setCurrentIndex(tree_item.index())
            return 0
        return 1

    def _delete_category(self, cat: Category, idx: QModelIndex) -> bool:
        delete = confirm_delete(self.window, cat)
        if not delete:
            return False
        self.notes_repo.delete_category(cat)
        self.navbar.model.removeRow(idx.row(), idx.parent())
        return True

    def _delete_file(self, file: SourceFile, idx: QModelIndex) -> bool:
        delete = confirm_delete(self.window, file)
        if not delete:
            return False
        if isinstance(file, Note):
            self.notes_repo.delete_note(file)
            self.navbar.model.removeRow(idx.row(), idx.parent())
            return True
        return False

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
        return_code = compile_source(file, options)
        svg_files = sorted(tmpdir_path.glob(f"{constants.OUTPUT_FILE_STEM}*.svg"), key=rendered_sorted_key)
        self._update_svg(svg_files, tmpdir, file_name)

    def _update_svg(self, path: Path | list[Path], tmpdir: tempfile.TemporaryDirectory, name: str | None=None):
        paths = path if isinstance(path, list) else [path]
        if all(p.exists() for p in paths):
            self.viewer.load_current_viewer([str(p) for p in paths], tmpdir=tmpdir, name=name)

    def _get_item_and_index(self) -> tuple[QStandardItem | None, None | QModelIndex]:
        idx = self.navbar.tree.currentIndex()
        if not idx.isValid(): #TODO error msg for top level
            return None, None
        item = self.navbar.model.itemFromIndex(idx)
        return item, idx


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

    def init_tree(self):
        for course in self.course_repo.courses().values():
            self.add_course(course)

    def connect_handlers(self):
        self.navbar.file_opened.connect(lambda f: self.handle_file_opened(f))
        self.navbar.delete.connect(lambda: self.handle_delete())
        self.navbar.new_course.connect(lambda: self.handle_new_course())
        self.navbar.new_assignment.connect(lambda: self.handle_new_course())
        self.navbar.new_lecture.connect(lambda: self.handle_new_course())

    def handle_new_course(self):
        dialog = NewCourseDialog()
        if dialog.exec():
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

    def handle_delete(self):
        # file => course or note.
        item, idx = self._get_item_and_index()
        if item is None or idx is None:
            return
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

    def handle_file_opened(self, file: SourceFile):
        # No tabs => Add tab
        tmpdir = tempfile.TemporaryDirectory()
        tmpdir_path = Path(tmpdir.name)

        options = CompileOptions(file.path, OutputFormat.SVG, multi_page=True)
        options.set_output_dir(tmpdir_path)
        options.set_output_file_stem(constants.OUTPUT_FILE_STEM)

        file_name = file.path.parent.parent.stem
        return_code = compile_source(file, options)
        svg_files = sorted(tmpdir_path.glob(f"{constants.OUTPUT_FILE_STEM}*.svg"), key=rendered_sorted_key)
        self._update_svg(svg_files, tmpdir, file_name)

    def _update_svg(self, path: Path | list[Path], tmpdir: tempfile.TemporaryDirectory, name: str | None=None):
        paths = path if isinstance(path, list) else [path]
        if all(p.exists() for p in paths):
            self.viewer.load_current_viewer([str(p) for p in paths], tmpdir=tmpdir, name=name)

    def _get_item_and_index(self) -> tuple[QStandardItem | None, None | QModelIndex]:
        idx = self.navbar.tree.currentIndex()
        if not idx.isValid(): #TODO error msg for top level
            return None, None
        item = self.navbar.model.itemFromIndex(idx)
        return item, idx

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
    def __init__(self):
        self.watcher = QFileSystemWatcher()
        self.watcher.addPath(constants.TYP_FILE_LIVE)

#    def on_typ_changed(self):
#        self.watcher.removePath(constants.TYP_FILE_LIVE)
#        self.watcher.addPath(constants.TYP_FILE_LIVE)
#        self.compile_typst(constants.TYP_FILE_LIVE)

#    def compile_typst(self, path: str):
#        self.process = QProcess()
#        self.process.start("typst", ["compile", path, "--format", "svg"])
#        self.process.finished.connect(lambda : self.update_svg(path))
