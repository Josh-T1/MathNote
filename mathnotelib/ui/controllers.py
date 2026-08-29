from io import UnsupportedOperation
import shutil
import tempfile
from pathlib import Path
import threading
import time
from typing import Callable, Literal
import logging
import random

from PyQt6.QtCore import QFileSystemWatcher, QModelIndex, QObject, QTimer, Qt
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QHBoxLayout, QListView, QMainWindow, QWidget


from .constants import DIR_ROLE, COURSE_CONTAINER_ROLE, COURSE_DIR, FILE_ROLE, LOADED_ROLE, OUTPUT_FILE_STEM
from .widgets import TightStackedWidget
from .flashcard_navbar import FlashcardNavbar
from .navbar import CourseNavbar, NavbarContainer, NotesNavbar, SettingsNavbar
from .dialog import NewCourseDialog, NameDialog, NewSectionDialog, NewTypesetFileDialog, ParentSelectDialog, confirm_delete
from .file_viewer import TabWidget, TabbedSvgViewer
from .flashcard_viewer import FlashcardView
from .dialog import show_error_dialog
from ..models import Category, Course, SourceFile, Note, FlashcardSideName
from ..services import (CompileOptions, compile_source, NotesRepository, CourseRepository, NotesRepository, FlashcardSession,
                        FlashcardCache, FlashcardCompiler, open_pdf, DeckRepository, DataGenerator, FlashcardBuilderStage, CleanStage, DataGenerator, ProcessingPipeline, FormatStage)
from ..config import CONFIG, Section
from ..enums import FileType, OutputFormat
from ..exceptions import (CompilationError, FlashcardCompilationError, LaTeXCompilationError, NoItemSelected, NoteExistsError, CategoryExistsError,
                          InvalidNameError, NoteExistsError, CourseExistsError, TypstCompilationError, FlashcardCompilationError, NoItemSelected)


logger = logging.getLogger("mathnote")


def with_error_dialog(func):
    def wrapper(self: NoteController | CourseController | FlashcardController, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except (NoteExistsError, CourseExistsError, InvalidNameError, CategoryExistsError) as e:
            show_error_dialog(self.window, str(e))
        except (LaTeXCompilationError, TypstCompilationError) as e:
            show_error_dialog(self.window, str(e))
        except Exception as e:
            show_error_dialog(self.window, f"Unexpected error: {e}")
    return wrapper


def rendered_sorted_key(path: Path) -> int:
    num = int(path.name.split(".")[0].split("-")[1])
    return num


class ViewContainer(QWidget):

    def __init__(self, notes_viewer: TabbedSvgViewer, flashcard_viewer: FlashcardView):
        super().__init__()
        self.notes_viewer = notes_viewer
        self.flashcard_viewer = flashcard_viewer
        self.view_stack = TightStackedWidget()
        self.initUi()

    def initUi(self):
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)

        self.view_stack.addWidget(self.notes_viewer)
        self.view_stack.addWidget(self.flashcard_viewer)
        self.view_stack.setCurrentWidget(self.notes_viewer)
        self.main_layout.addWidget(self.view_stack)


class ViewController(QObject):
    def __init__(self, window: QMainWindow, navbar_container: NavbarContainer, view_container: ViewContainer):
        super().__init__()
        self.window = window
        self.navbar_cont = navbar_container
        self.window_cont = view_container
        self.connect_handlers()

    def connect_handlers(self):
        self.navbar_cont.notes_btn.clicked.connect(lambda: self.set_notes_view())
        self.navbar_cont.courses_btn.clicked.connect(lambda: self.set_course_notes_view())
        self.navbar_cont.flashcards_btn.clicked.connect(lambda: self.set_flashcard_view())
        self.navbar_cont.minimize_btn.clicked.connect(lambda: self.toggle_navbar_container())
        self.navbar_cont.collapsed_widget.expand_btn.clicked.connect(lambda: self.toggle_navbar_container())
        self.navbar_cont.settings_btn.clicked.connect(lambda: self.set_settings_view())

    def set_settings_view(self):
        self.navbar_cont.stack.setCurrentWidget(self.navbar_cont.settings_navbar)

    def toggle_navbar_container(self):
        diff = self.navbar_cont.visible_widget.width() - self.navbar_cont.collapsed_widget.width()
        current_width = self.window.width()
        current_height = self.window.height()

        if self.navbar_cont.container_stack.currentWidget() == self.navbar_cont.collapsed_widget:
            self.navbar_cont.container_stack.setCurrentWidget(self.navbar_cont.visible_widget)
            self.window.setMinimumWidth(1050)

        else:
            self.navbar_cont.container_stack.setCurrentWidget(self.navbar_cont.collapsed_widget)
            self.window.setMinimumWidth(current_width - diff)
            self.window.resize(current_width - diff, current_height)

    def set_flashcard_view(self):
        self.navbar_cont.stack.setCurrentWidget(self.navbar_cont.flashcard_navbar)
        self.window_cont.view_stack.setCurrentWidget(self.window_cont.flashcard_viewer)
        self.window.setFixedSize(1050, 860)

    def set_notes_view(self):
        self.navbar_cont.stack.setCurrentWidget(self.navbar_cont.notes_navbar)
        self.window_cont.view_stack.setCurrentWidget(self.window_cont.notes_viewer)
        self.window.setMinimumSize(1050, 1000)
        self.window.setMaximumSize(16777215, 16777215)

    def set_course_notes_view(self):
        self.navbar_cont.stack.setCurrentWidget(self.navbar_cont.courses_navbar)
        self.window_cont.view_stack.setCurrentWidget(self.window_cont.notes_viewer)
        self.window.setMinimumSize(1050, 1000)
        self.window.setMaximumSize(16777215, 16777215)  # Qt's default max



class NoteController(QObject):
    def __init__(self, window: QMainWindow, navbar: NotesNavbar, viewer: TabbedSvgViewer):
        super().__init__()
        self.window = window
        self.navbar = navbar
        self.viewer = viewer
        self.current_notes_repo: NotesRepository | None = None
        self.notes_repositories: dict[str, NotesRepository] = self._load_repositories()
        self.connect_handlers()
        self._populate_view()


    def connect_handlers(self):
        self.navbar.new_note.connect(lambda: self.handle_create("Note"))
        self.navbar.file_opened.connect(lambda f: self.handle_file_opened(f))
        self.navbar.new_category.connect(lambda: self.handle_create("Category"))
        self.navbar.delete.connect(lambda: self.handle_delete())
        self.navbar.rename.connect(lambda: self.handle_rename())
        self.navbar.load_item.connect(lambda item, cat: self.handle_load_item(item, cat))
        self.navbar.move_item.connect(lambda item, cat: self.handle_move_item(item, cat))
        self.navbar.new_repository.connect(lambda: self.handle_new_repository())
        self.navbar.delete_repository.connect(lambda: self.handle_delete_repository())
        self.navbar.change_respository.connect(lambda: self.handle_change_repository())


    def _load_repositories(self) -> dict[str, NotesRepository]:
        repos = {}
        for dir in CONFIG.note_repo_dir.iterdir():
            if not dir.is_dir():
                continue
            repo = NotesRepository(dir)
            repos[repo.name] = repo
            # TODO
            if repo.root_category.metadata.get("open") is True:
                self.current_notes_repo = repo

        list_repos = list(repos.values())
        if self.current_notes_repo is None and len(list_repos) > 0:
            self.current_notes_repo = list_repos[0]
        return repos

    @with_error_dialog
    def handle_new_repository(self):
        name_dialog = NameDialog()
        if not name_dialog.exec():
            return
        name = name_dialog.get_data()
        new_repo_path = CONFIG.note_repo_dir / name
        if new_repo_path.is_dir():
            return
        new_repo_path.mkdir()
        new_repo = NotesRepository(new_repo_path)
        self.notes_repositories[new_repo.name] = new_repo
        self.current_notes_repo = new_repo
        self.navbar.repo_combo.addItem(new_repo.name)
        self.navbar.repo_combo.setCurrentIndex(self.navbar.repo_combo.count()-1)

    @with_error_dialog
    def handle_delete_repository(self):
        repo = self.current_notes_repo
        if repo is None:
            return
        delete = confirm_delete(self.window, repo.name)
        if not delete:
            return
        idx = self.navbar.repo_combo.findText(repo.name)
        shutil.rmtree(repo.repo_root)
        del self.notes_repositories[repo.name]
        if idx != -1:
            self.navbar.repo_combo.removeItem(idx)


    @with_error_dialog
    def handle_change_repository(self):
        new_repo_name = self.navbar.repo_combo.currentText()
        new_repo = self.notes_repositories[new_repo_name]
        for repo in self.notes_repositories.values():
            repo.root_category.metadata["open"] = False
        new_repo.root_category.metadata["open"] = True
        self.current_notes_repo = new_repo
        self._populate_list_view()

    @with_error_dialog
    def handle_move_item(self, data: dict, parent_idx: QModelIndex):
        if self.current_notes_repo is None:
            return
        item_type, path = data["type"], data["path"]
        parent = self.navbar.model.itemFromIndex(parent_idx) or self.navbar.root_item()
        parent_cat = parent.data(DIR_ROLE)
        if parent_cat is None:
            raise Exception("Missing data from tree item")

        if item_type == "Note":
            note = self.current_notes_repo.path_to_note(path)
            old_parent = note.category
            self.current_notes_repo.rename_note(note, note.name, parent_cat)
        else:
            category = self.current_notes_repo.path_to_category(path)
            old_parent = category.parent
            assert old_parent is not None, "Attempting to move root category" # Is this necessary? should be impossible

            self.current_notes_repo.rename_cat(category, category.name, parent_cat)
        valid = self.navbar.model.complete_move()
        self.handle_load_item(parent, parent_cat)

    def handle_load_item(self, item: QStandardItem, cat: Category):
        if self.current_notes_repo is None:
            return
        item.removeRows(0, item.rowCount())
        subcategories = self.current_notes_repo.get_sub_categories(cat)
        for sub_cat in subcategories:
            item.appendRow(self.navbar._build_cat_item(sub_cat))

        for note in cat.notes:
            item.appendRow(self.navbar._build_file_item(note))

        if len(cat.notes) + len(subcategories) > 0:
            item.setData(True, LOADED_ROLE)

    def _populate_view(self):
        repos = list(self.notes_repositories.keys())
        for name, repo in self.notes_repositories.items():
            if repo.root_category.metadata.get("open") == True:
                self.current_notes_repo = repo
                repos.sort(key=lambda repo_name: (repo_name != name, repo_name))
                break
        self.navbar.repo_combo.addItems(repos)
        self._populate_list_view()

    def _populate_list_view(self):
        if self.current_notes_repo is None:
            return
        self.navbar.model.clear()
        self.navbar.root_item().setData(self.current_notes_repo.root_category, DIR_ROLE)
        sub_categories = self.current_notes_repo.get_sub_categories(self.current_notes_repo.root_category)
        for child in sub_categories:
            self.navbar.root_item().appendRow(self.navbar._build_cat_item(child))

        for note in self.current_notes_repo.root_category.notes:
            self.navbar.root_item().appendRow(self.navbar._build_file_item(note))

    @with_error_dialog
    def handle_rename(self):
        if self.current_notes_repo is None:
            return
        item, idx = self.navbar._get_item_and_index()
        if item is None:
            return
        parent = item.parent() or self.navbar.root_item()
        dialog = NameDialog()
        if not dialog.exec():
            return
        name = dialog.get_data()

        if (file := item.data(FILE_ROLE)) is not None:
            assert isinstance(file, Note), f"Tree item has unexpected type: '{type(file)}', expected 'Note'"
            renamed_obj = self.current_notes_repo.rename_note(file, name)
            target_category = None if renamed_obj is None else renamed_obj.category

        elif (cat := item.data(DIR_ROLE)) is not None:
            assert isinstance(cat, Category), f"Tree item has unexpected type: '{type(file)}', expected 'Note'"
            renamed_obj = self.current_notes_repo.rename_cat(cat, name)
            target_category = None if renamed_obj is None else renamed_obj.parent or self.current_notes_repo.root_category
        else:
            return
        if target_category is not None:
            self.handle_load_item(parent, target_category)

    def _delete_item(self, item: Note | Category, idx: QModelIndex) -> bool:
        if self.current_notes_repo is None:
            return False
        delete = confirm_delete(self.window, item.name)
        if not delete:
            return False
        del_map = {
                Category: self.current_notes_repo.delete_category,
                Note: self.current_notes_repo.delete_note
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

        if (dir := item.data(DIR_ROLE)) is not None:
            assert isinstance(dir, Category), f"Tree item has unexpected type: '{type(dir)}', expected 'Category'"

            delete = self._delete_item(dir, idx)

        elif (file := item.data(FILE_ROLE)) is not None:
            assert isinstance(file, Note), f"Tree item has unexpected type: '{type(file)}', expected 'Note'"
            delete = self._delete_item(file, idx)
        else:
            return

        if parent is not None and parent.rowCount() == 0 and delete:
            self.navbar.tree.collapse(parent.index())
            parent.setData(False, LOADED_ROLE)

    @with_error_dialog
    def handle_create(self, item_type: Literal["Note"] | Literal["Category"]):
        if self.current_notes_repo is None:
            return
        item, idx = self.navbar._get_item_and_index()
        # Given item we determine parent_item in tree (depends on isExpanded()) and set cat to be parent category
        if item is None or idx is None:
            parent_item = self.navbar.root_item()
            cat = self.current_notes_repo.root_category

        elif (note := item.data(FILE_ROLE)) is not None:
            assert isinstance(note, Note), f"Tree item has unexpected type: '{type(note)}', expected 'Note'"

            cat = note.category
            parent_item = item.parent() or self.navbar.root_item()

        elif (cat := item.data(DIR_ROLE)) is not None:
            assert isinstance(cat, Category), f"Tree item has unexpected type: '{type(cat)}', expected 'Category'"
            # If tree expanded around category item => parent in tree is selected item
            if self.navbar.tree.isExpanded(idx):
                cat: Category = item.data(DIR_ROLE)
                parent_item = item
            # If tree not expanded => parent in tree is selected items parent
            else:
                parent_item = item.parent() or self.navbar.root_item()
                cat: Category = parent_item.data(DIR_ROLE)
        else:
            return
        # Now that parent item in tre is set, we create relevant files/dir's and add to tree
        if item_type == "Note":
            dialog = NewTypesetFileDialog()
            if not dialog.exec(): return
            name, ftype = dialog.get_data()
            note = self.current_notes_repo.create_note(name, cat, ftype)
            res_item = self.navbar._build_file_item(note)

            self.viewer.addTab(note, focus=True)
            self.navbar.file_opened.emit(note)
            self.navbar.tree.setCurrentIndex(res_item.index())
        else:
            dialog = NameDialog()
            if not dialog.exec(): return
            name = dialog.get_data()
            res = self.current_notes_repo.create_category(name, cat)
            res_item = self.navbar._build_cat_item(res)

        if parent_item is not None: # Should be impossible
            parent_item.appendRow(res_item)
            self.navbar.tree.expand(parent_item.index())

    @with_error_dialog
    def handle_file_opened(self, file: SourceFile):
        tmpdir = tempfile.TemporaryDirectory()
        tmpdir_path = Path(tmpdir.name)

        options = CompileOptions(file.path, OutputFormat.SVG, multi_page=True)
        options.set_output_dir(tmpdir_path)
        options.set_output_file_stem(OUTPUT_FILE_STEM)
        options.set_cwd(file.path.parent.parent)
        options.root = file.path.parent.parent

        name_func: Callable[[], str] = getattr(file, "pretty_name", lambda: file.name)
        compilation_res = compile_source(file, options)
        svg_files = sorted(tmpdir_path.glob(f"{OUTPUT_FILE_STEM}*.svg"), key=rendered_sorted_key)
        if len(svg_files) == 0:
            raise CompilationError(compilation_res[1])
        self._update_svg(svg_files, tmpdir, file)

    def _update_svg(self, path: Path | list[Path], tmpdir: tempfile.TemporaryDirectory, source: SourceFile | None=None):
        paths = path if isinstance(path, list) else [path]
        if all(p.exists() for p in paths):
            self.viewer.load_current_viewer([str(p) for p in paths], tmpdir=tmpdir, source=source)


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


class LiveTypstController:
    DEBOUNCE = 20

    def __init__(self, window: QMainWindow, viewer: TabbedSvgViewer):
        super().__init__()
        self.viewer = viewer
        self.viewer.tab_changed.connect(self.update_tab)
        self.window = window # Used by @with_error_dialog
        self.live_file: SourceFile | None = None
        self.live_files: list[SourceFile] = []

        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self.compile_typst)

        self.watcher = QFileSystemWatcher()
        self.watcher.fileChanged.connect(lambda path: self.on_typ_changed(path))

        self.connect_handlers()

    def update_tab(self) -> None:
        for tab in self.viewer.tab_bar.get_tabs():
            if not tab.is_focused:
                continue
            sc = tab.source_file
            if sc is None:
                return
            current_tab = self.viewer.tab_bar.get_focused_tab()
            if current_tab is None:
                return
            self.live_file = current_tab.source_file
            self.compile_typst()
            return

    @with_error_dialog
    def toggle_live_preview(self) -> bool:
        source_file: None | SourceFile = None
        is_live: bool = False

        layout = self.viewer.tab_bar.main_layout

        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is None:
                continue
            tab = item.widget()
            if not isinstance(tab, TabWidget):
                continue
            if not tab.is_focused:
                continue
            source_file = tab.source_file
            is_live = tab.is_live

        if source_file is None:
            return False

        if source_file.path.suffix != ".typ":
            raise UnsupportedOperation(f"Live preview is only supported for typst files (.typ) not '{source_file.path.suffix}'")

        if is_live:
            self.watcher.removePath(str(source_file.path))
        else:
            self.watcher.addPath(str(source_file.path))
        return True

    def connect_handlers(self):
        self.viewer.tab_bar.preview.connect(self.toggle_live_preview)
        self.viewer.tab_bar.preview.connect(self.viewer.tab_bar.toggle_live)

    def on_typ_changed(self, path: str):
        current_tab = self.viewer.tab_bar.get_focused_tab()
        if current_tab is None:
            return

        self.live_file = current_tab.source_file

        if self.live_file is None or str(self.live_file.path) != path or not current_tab.is_live:
            return

        if self._debounce_timer and not self._debounce_timer.isActive():
            self._debounce_timer.start(self.DEBOUNCE)

    @with_error_dialog
    def compile_typst(self):
        if self.live_file is None:
            return
        tmpdir = tempfile.TemporaryDirectory() # Does this get cleaned up?
        tmpdir_path = Path(tmpdir.name)

        options = CompileOptions(self.live_file.path, OutputFormat.SVG, multi_page=True)
        options.set_output_dir(tmpdir_path)
        options.set_output_file_stem(OUTPUT_FILE_STEM)

        compilation_res = compile_source(self.live_file, options)
        svg_files = sorted(tmpdir_path.glob(f"{OUTPUT_FILE_STEM}*.svg"), key=rendered_sorted_key)
        if len(svg_files) == 0: #TODO seems like live compile breaks this
            return

        self._update_svg(svg_files, tmpdir, self.live_file)

    def _update_svg(self,
                    path: Path | list[Path],
                    tmpdir: tempfile.TemporaryDirectory,
                    source: SourceFile | None=None,
                    ):
        paths = path if isinstance(path, list) else [path]
        if all(p.exists() for p in paths):
            self.viewer.load_current_viewer([str(p) for p in paths], tmpdir=tmpdir, source=source, preserve_state=True)


class FlashcardController:
    def __init__(self, window: QMainWindow, navbar: FlashcardNavbar, view: FlashcardView):
        super().__init__()
        self.window = window
        self.navbar = navbar
        self.view = view
        self.deck_repo = DeckRepository(CONFIG)
        self.cache = FlashcardCache(CONFIG.cache_dir())
        self.compiler = FlashcardCompiler(self.cache)
        self.session = FlashcardSession(self.compiler)
        self.course_repo = CourseRepository(CONFIG)

        self.set_handlers()
        self._populate_view()


    def set_handlers(self):
        self.view.btn_bar.next_flashcard_button.clicked.connect(lambda: self.show_next_flashcard())
        self.view.btn_bar.prev_flashcard_button.clicked.connect(lambda: self.show_prev_flashcard())
        self.navbar.create_cards_btn.clicked.connect(lambda: self.create_flashcards())
        self.view.info_bar.info_button.clicked.connect(lambda: self.show_flashcard_info())
        self.navbar.course_config.update_filters.connect(lambda: self.handle_update_filters())
        self.session.pos.connect(lambda x, y: self.handle_update_count(x, y))
        self.navbar.deck_config.new_deck_btn.clicked.connect(lambda: self.handle_new_deck())
        self.navbar.deck_config.trash_btn.clicked.connect(lambda: self.handle_delete_deck())
        self.navbar.deck_config.rename_btn.clicked.connect(lambda: self.handle_rename_deck())

    @with_error_dialog
    def handle_rename_deck(self):
        curr_name = self.navbar.deck_config.deck_combo.currentText()
        idx = self.navbar.deck_config.deck_combo.currentIndex()
        dialog = NameDialog()
        if not dialog.exec():
            return
        new_name = dialog.get_data()
        self.deck_repo.rename_deck(curr_name, new_name)
        self.navbar.deck_config.deck_combo.setItemText(idx, new_name)

    @with_error_dialog
    def handle_delete_deck(self):
        name = self.navbar.deck_config.deck_combo.currentText()
        idx = self.navbar.deck_config.deck_combo.currentIndex()
        delete = confirm_delete(self.window, name)
        if not delete:
            return
        self.deck_repo.delete_deck(name)
        self.navbar.deck_config.deck_combo.removeItem(idx)


    @with_error_dialog
    def handle_new_deck(self):
        dialog = NewTypesetFileDialog()
        if not dialog.exec():
            return
        name, ftype = dialog.get_data()
        self.deck_repo.new_deck(name, ftype)
        self.navbar.deck_config.deck_combo.addItem(name)
        self.navbar.deck_config.deck_combo.setCurrentIndex(self.navbar.deck_config.deck_combo.count() - 1)


    @with_error_dialog
    def handle_update_filters(self):
        text = self.navbar.course_config.course_combo.currentText()
        course = self.course_repo.get_course(text)
        if course is None:
            raise ValueError("Course directory not found")

        model = self.navbar.course_config.filter_by_lecture_list_model
        model.clear()
        all_box = QStandardItem('All')
        all_box.setCheckable(True)
        model.appendRow(all_box)
        for i in range(1, len(course.lectures)):
            list_item = QStandardItem(f"Lecture {i}")
            list_item.setCheckable(True)
            model.appendRow(list_item)



    @with_error_dialog
    def show_next_flashcard(self, first=False):
        card = self.session.next_flashcard(first=first)
        try:
            self.view.display_compiled_card(card)
        except Exception as e:
            ans = card.sides.get(FlashcardSideName.ANSWER)
            pf = card.sides.get(FlashcardSideName.PROOF)

            if ans is None and pf is None:
                question = card.sides[FlashcardSideName.QUESTION].content
                raise ValueError(f"Missing second side\n Flashcard question: {question}\n source: {question.source}")

            if ans is not None and ans.pdf_path is None:
                ans.pdf_path = self.compiler.text_to_pdf(str(ans.content))

            if pf is not None and pf.pdf_path is None:
                pf.pdf_path = self.compiler.text_to_pdf(str(pf.content))

            self.view.display_compiled_card(card)
            raise FlashcardCompilationError("Failed to compile flashcard. Displaying raw LaTeX/Typst")


    def handle_update_count(self, current: int, total: int):
        self.view.info_bar.set_count(current, total)


    @with_error_dialog
    def show_prev_flashcard(self):
        logger.debug(f"Calling {self.show_prev_flashcard}")
        card = self.session.prev_flashcard()
        self.view.display_compiled_card(card)

    def show_flashcard_info(self):
        card = self.session.current_card
        if card is None:
            message = "No flashcards have been loaded"
            self.view.info_bar.info_button.set_message(message)
            return

        info = card.sides[FlashcardSideName.QUESTION].content.source
        if info is None:
            message = "No flashcards have been loaded"
            return
        else:
            message = f"Source: {info}"
        self.view.info_bar.info_button.set_message(message)

    def create_flashcards(self):
        if self.navbar.stack.currentWidget() == self.navbar.course_config:
            paths, section_names_dict, shuffle = self.generate_pipe_course_config()
            logger.info(f"Creating flashcards from {len(paths)} paths")
        else:
            path, section_names_dict, shuffle = self.generate_pipe_deck_config()
            paths = [path]

        data_iterable = DataGenerator(paths)
        clean_data_stage = CleanStage(CONFIG.macros)
        format_state = FormatStage()
        build_stage = FlashcardBuilderStage(section_names_dict)
        # TODO
        build_stage.add_subsection_finder("Proof")
        pipeline = ProcessingPipeline(data_iterable)
        pipeline.add_stage(clean_data_stage)
        pipeline.add_stage(build_stage)
        pipeline.add_stage(format_state)

        load_thread = threading.Thread(target=self.session.load_flashcards, args=(pipeline, shuffle))
        load_thread.start()

        time.sleep(0.1)
        self.show_next_flashcard(first=True)

    def stop(self):
        self.session.stop()

    def generate_pipe_deck_config(self) -> tuple[Path, dict[str, Section], bool]:
        filename = self.navbar.deck_config.deck_combo.currentText()
        path = self.deck_repo.decks.get(filename)
        if path is None:
            raise ValueError("Deck with name '{filename}' is not recognized")

        shuffle = self.navbar.deck_config.random_checkbox.isChecked()
        checked_sections = self._get_checked_items_from_listView(self.navbar.deck_config.section_list.section_list)
        section_names_pretty = [item.text().upper() for item in checked_sections]
        if "ALL" in [section.upper() for section in section_names_pretty]:
            section_names = CONFIG.section_names
        else:
            section_names = {k: d for (k, d) in CONFIG.section_names.items() if k in section_names_pretty}
        return path, section_names, shuffle

    def generate_pipe_course_config(self) -> tuple[list[Path], dict[str, Section], bool]:
        """ Retreives user config from widgets. We need to do error checking... what if no boxes are checked """
        # Lecture numberes
        course_name = self.navbar.course_config.course_combo.currentText()
        course = self.course_repo.get_course(course_name)
        if not course:
            raise ValueError(f"Course name {course} not recognized")
        lec_list_items = self._get_checked_items_from_listView(self.navbar.course_config.filter_by_lecture_list)
        lec_text_items = [lec.text() for lec in lec_list_items]
        if "ALL" in [lec.upper() for lec in lec_text_items] or not lec_text_items:
            lectures = {i for i in range(1, len(course.lectures))}
        else:
            lectures = {int(lecture.split(" ")[-1]) for lecture in lec_text_items}

        # Sections
        checked_sections = self._get_checked_items_from_listView(self.navbar.course_config.section_list.section_list)
        section_names_pretty = [item.text().upper() for item in checked_sections]
        if "ALL" in [section.upper() for section in section_names_pretty]:
            section_names = CONFIG.section_names
        else:
            section_names = {k: d for (k, d) in CONFIG.section_names.items() if k in section_names_pretty}

        # Filter paths and shuffle
        shuffle = self.navbar.course_config.random_checkbox.isChecked()
        paths = [lecture.path for lecture in course.lectures if lecture.number() in lectures]
        if shuffle:
            random.shuffle(paths)

        return paths, section_names, shuffle

    def _get_checked_items_from_listView(self, listview: QListView):
        """ Given a QListView object, all items that are in the 'checked' state are returned """
        checked_items = []
        model: QStandardItemModel | None = listview.model() #type: ignore
        if model:
            for i in range(model.rowCount()):
                item = model.item(i)
                if item and item.checkState() == Qt.CheckState.Checked: #type: ignore
                    checked_items.append(item)
        return checked_items

    def open_main(self):
        course_name = self.navbar.course_config.course_combo.currentText()
        course = self.course_repo.get_course(course_name)
        if not course:
            raise ValueError(f"Course name {course} not recognized")
        open_pdf(course.main_file)

    def _populate_view(self):
        courses = self.course_repo.courses().keys()
        self.navbar.course_config.course_combo.addItems(courses)
        keys = ["All"]
        keys.extend([name.lower().capitalize() for name in list(CONFIG.section_names.keys())])
        self.navbar.course_config.section_list.add_items(keys)
        self.navbar.deck_config.section_list.add_items(keys)
        self.navbar.deck_config.deck_combo.addItems(list(self.deck_repo.decks.keys()))


LABEL_ROLE = Qt.ItemDataRole.UserRole + 20   # which field this value-item maps to, e.g. "latex" / "typst"
SECTION_ROLE = Qt.ItemDataRole.UserRole + 21 # the section object, stored on the parent row
PARENTS_ROLE = Qt.ItemDataRole.UserRole + 22 # the section object, stored on the parent row


class SettingsController(QObject):
    def __init__(self, window: QMainWindow, settings_navbar: SettingsNavbar):
        super().__init__()
        self.settings_nav = settings_navbar
        self.window = window
        self._populate_view()
        self.connect_handlers()

    def connect_handlers(self):
        self.settings_nav.new_section.connect(lambda: self.handle_new_section())
        self.settings_nav.delete_section.connect(lambda: self.handle_delete_section())
        self.settings_nav.pattern_changed.connect(lambda: self.pattern_changed())
        self.settings_nav.save_btn.clicked.connect(lambda: self.handle_save())
        self.settings_nav.section_view.doubleClicked.connect(self._on_item_double_clicked)

    @with_error_dialog
    def handle_save(self):
        CONFIG.save()

    @with_error_dialog
    def handle_new_section(self):
        dialog = NewSectionDialog()
        if not dialog.exec():
            return
        name, typ_ptrn, tex_ptrn = dialog.get_data()
        if not typ_ptrn or not tex_ptrn:
            raise ValueError("File pattern for both Typst and LaTeX files")
        if not name:
            raise ValueError("Null section name provided. Section name must be specified")
        new_section = Section(name,{FileType.LaTeX: tex_ptrn, FileType.Typst: typ_ptrn})
        CONFIG.section_names[name] = new_section
        self._build_section(name, new_section)

    @with_error_dialog
    def handle_delete_section(self):
        idx = self.settings_nav.section_view.currentIndex()
        if not idx.isValid():
            return None
        item = self.settings_nav.section_model.itemFromIndex(idx)
        if item is None:
            return
        if item.parent() is not None:
            return None
        section_name = item.data(SECTION_ROLE)
        dependents = [
            name for name, section in CONFIG.section_names.items()
            if section_name in section.parents
        ]
        if dependents:
            raise ValueError(
                f"Cannot delete '{section_name}': it is a required parent for {', '.join(dependents)}"
            )

        confirmed = confirm_delete(self.window, section_name)
        if not confirmed:
            return

        idx = item.index()
        self.settings_nav.section_model.removeRow(idx.row(), idx.parent())
        del CONFIG.section_names[section_name]
        return

    @with_error_dialog
    def pattern_changed(self):
        return

    def _build_section(self, name: str, ftype_map):
        section_item = self._build_section_row(name, ftype_map)
        self.settings_nav.section_model.appendRow(section_item)
        index = self.settings_nav.section_model.indexFromItem(section_item)
        self.settings_nav.section_view.setFirstColumnSpanned(
            index.row(), index.parent(), True
        )

    def _populate_view(self):
        self.settings_nav.root_val.set_path(str(CONFIG.root_path))

        for name, ftype_map in CONFIG.section_names.items():
            self._build_section(name, ftype_map)

    def _build_parent_row(self, section_name: str, parents: frozenset[str]):
        label_item = QStandardItem("Parents")
        label_flags = label_item.flags()
        label_flags &= ~Qt.ItemFlag.ItemIsEditable
        label_item.setFlags(label_flags)

        display_text = ", ".join(sorted(parents)) if parents else "(none)"
        value_item = QStandardItem(display_text)
        value_flags = value_item.flags()
        value_flags |= Qt.ItemFlag.ItemIsEditable
        value_item.setFlags(value_flags)
        value_item.setData(section_name, SECTION_ROLE)
        value_item.setData("parents", LABEL_ROLE)
        value_item.setData(parents, PARENTS_ROLE)
        return [label_item, value_item]

    def _build_section_row(self, section_name: str, section: Section) -> QStandardItem:
        name_item = QStandardItem(section_name)
        flags = name_item.flags()
        flags &= ~Qt.ItemFlag.ItemIsEditable
        name_item.setFlags(flags)
        name_item.setData(section_name, SECTION_ROLE)
        name_item.appendRow(self._build_pattern_row("LaTeX", section_name, section.patterns[FileType.LaTeX]))
        name_item.appendRow(self._build_pattern_row("Typst", section_name, section.patterns[FileType.Typst]))
        name_item.appendRow(self._build_parent_row(section_name, section.parents))
        return name_item

    def _build_pattern_row(self, label: str, section, value: str) -> list[QStandardItem]:
        label_item = QStandardItem(label)
        label_flags = label_item.flags()
        label_flags &= ~Qt.ItemFlag.ItemIsEditable
        label_item.setFlags(label_flags)

        value_item = QStandardItem(value)
        value_flags = value_item.flags()
        value_flags |= Qt.ItemFlag.ItemIsEditable
        value_item.setFlags(value_flags)
        value_item.setData(section, SECTION_ROLE)
        value_item.setData(label, LABEL_ROLE)
        return [label_item, value_item]


    def _on_item_double_clicked(self, index: QModelIndex):
        item = self.settings_nav.section_model.itemFromIndex(index)
        if item is None or item.data(LABEL_ROLE) != "parents":
            return  # not a parents row — let normal inline editing happen for pattern rows

        section_name = item.data(SECTION_ROLE)
        current_parents = item.data(PARENTS_ROLE)
        all_names = list(CONFIG.section_names.keys())

        dialog = ParentSelectDialog(all_names, section_name, current_parents)
        if not dialog.exec():
            return

        new_parents = dialog.get_selected()
        item.setData(new_parents, PARENTS_ROLE)
        item.setText(", ".join(sorted(new_parents)) if new_parents else "(none)")

        # persist to CONFIG immediately, or batch until save_btn — your call
        old_section = CONFIG.section_names[section_name]
        CONFIG.section_names[section_name] = Section(
            name=section_name, patterns=old_section.patterns, parents=new_parents
        )
