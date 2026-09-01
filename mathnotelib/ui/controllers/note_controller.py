import shutil
import tempfile
from pathlib import Path
from typing import Callable, Literal

from PyQt6.QtCore import QModelIndex, QObject
from PyQt6.QtGui import QStandardItem
from PyQt6.QtWidgets import QMainWindow

from .ui_utils import with_error_dialog, rendered_sorted_key
from ..constants import DIR_ROLE,  FILE_ROLE, LOADED_ROLE, OUTPUT_FILE_STEM
from ..navbar import NotesNavbar
from ..dialog import NameDialog, NewTypesetFileDialog, confirm_delete
from ..file_viewer import TabbedSvgViewer
from ...models import Category, SourceFile, Note
from ...services import CompileOptions, compile_source, NotesRepository, NotesRepository

from ...config import CONFIG
from ...enums import OutputFormat
from ...exceptions import CompilationError, NoItemSelected


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
