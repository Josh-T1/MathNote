import tempfile
from pathlib import Path
from typing import Protocol, Callable, Optional

from PyQt6.QtGui import QBrush, QMouseEvent, QPalette, QStandardItem, QStandardItemModel, QTransform
from PyQt6.QtWidgets import (QApplication, QButtonGroup, QFrame, QGestureEvent, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QListWidget, QMainWindow, QPinchGesture, QPushButton, QScrollArea, QSizePolicy,
                             QSpacerItem, QStyle, QStyleOptionViewItem, QToolBar, QTreeView, QVBoxLayout, QWidget)
from PyQt6.QtCore import QEvent, QFileSystemWatcher, QModelIndex, QProcess, QTimer, pyqtSignal, Qt

from .style import MAIN_WINDOW_CSS, SVG_VIEWER_CSS, TOGGLE_BUTTON_CSS, TREE_VIEW_CSS
from . import constants
from ..utils import FileType, config, rendered_sorted_key
from ..structure import NotesManager, Courses, Category, OutputFormat, CompileOptions, SourceFile,Note
from ..flashcard import FlashcardMainWindow, CompilationManager, FlashcardModel, FlashcardController


class UpdateSvgCallback(Protocol):
    def __call__(self, path: list[str], tmpdir: Optional[tempfile.TemporaryDirectory]) -> None:...


class LauncherWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_layout = QVBoxLayout()
        self.btn_layout = QHBoxLayout()
        self.btn_container = QWidget()
        self.setLayout(self.main_layout)
        self.btn_container.setLayout(self.btn_layout)
        self.setContentsMargins(0, 0, 0, 0)
        self.initUI()

    def initUI(self):
        self._create_widgets()
        self._configure_widgets()
        self._add_widgets()

    def _create_widgets(self):
        self.launch_label = QLabel("Launch")
        self.flashcard_button = QPushButton("Flashcards")

    def _add_widgets(self):
        self.btn_layout.addWidget(self.flashcard_button, Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.launch_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.btn_container, alignment=Qt.AlignmentFlag.AlignCenter)

    def _configure_widgets(self):
        self.flashcard_button.setFixedWidth(100)
        self.flashcard_button.clicked.connect(self.launch_flashcards)

    # TODO ensure that we wait for flashcards to terminate properly
    def launch_flashcards(self):
        self.compilation_manager = CompilationManager()
        self.flashcard_model = FlashcardModel(self.compilation_manager)
        self._window = FlashcardMainWindow()
        self.controller = FlashcardController(self._window, self.flashcard_model, config) #type: ignore
        self._window.setCloseCallback(self.controller.close)
        self.controller.run(None)


class Navbar(QWidget):
    file_opened = pyqtSignal(str)

    def __init__(self, callback: UpdateSvgCallback):
        """
        callback: callable with str argument, should be a valid typst path
        """
        super().__init__()
        self.tree_visible: bool = True
        self.update_svg_func = callback

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        self.setLayout(self.main_layout)
        self.setFixedWidth(200)

        self.root_course_cat = NotesManager.build_root_category(constants.NOTES_DIR)
        self.initUI()

    def initUI(self):
        self._create_widgets()
        self._configure_widgets()
        self._add_widgets()
        self.populate_tree()

    def _create_widgets(self):
        self.toggle_button = QPushButton("x")
        self.new_note_button = QPushButton("new note")
        self.new_cat_button = QPushButton("new cat")
        self.mode_selector = ModeSelector()

        self.menu_bar_layout = QHBoxLayout()
        self.model = QStandardItemModel()
        self.tree = QTreeView()
        self.root_item = self.model.invisibleRootItem()
        self.launcher_widget = LauncherWidget()

    def _configure_widgets(self):
        # Main layout
        self.toggle_button.setStyleSheet(TOGGLE_BUTTON_CSS)
        self.toggle_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
#        self.toggle_button.clicked.connect(self.toggle_tree)

        self.tree.setModel(self.model)
        self.tree.setFrameShape(QFrame.Shape.NoFrame)
        self.tree.header().hide() #TODO: don't think header() every returns None..
        self.tree.expanded.connect(self._expand_callback)
        self.tree.setStyleSheet(TREE_VIEW_CSS)
        self.tree.clicked.connect(self._item_clicked_callback)

    def _add_widgets(self):
        self.menu_bar_layout.addWidget(self.toggle_button)
        self.menu_bar_layout.addWidget(self.new_note_button)
        self.menu_bar_layout.addWidget(self.new_cat_button)
#        self.hidden_layout.setFixedWidth(40)
        self.menu_bar_layout.addSpacerItem(QSpacerItem(15, 15, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        self.main_layout.addLayout(self.menu_bar_layout)
        self.main_layout.addWidget(self.tree)
        self.main_layout.addWidget(self.mode_selector)
        self.main_layout.addWidget(self.launcher_widget)

    def _expand_callback(self, index: QModelIndex):
        # Remark: the item will originally expand with the placeholder element. Once this occurs
        # we will remove placeholder and populate with correct options. This could give rise to a bug where placeholder persists
        item = self.model.itemFromIndex(index)
        if item is None:
            return
        cat = item.data(constants.DIR_ROLE)
        loaded = item.data(constants.LOADED_ROLE)
        if cat is not None and loaded is not None:
            if loaded is False:
                self._load_item(item, cat)

    def _item_clicked_callback(self, index: QModelIndex):
        item = self.model.itemFromIndex(index)
        if item is None:
            return

        # TODO: handle failed compilation
        if item.data(constants.FILE_ROLE) is not None:

            file: SourceFile = item.data(constants.FILE_ROLE)
            tmpdir = tempfile.TemporaryDirectory()
            tmpdir_path = Path(tmpdir.name)

            options = CompileOptions(file.path, OutputFormat.SVG, multi_page=True)
            options.set_output_dir(tmpdir_path)
            options.set_output_file_stem(constants.OUTPUT_FILE_STEM)

            return_code = file.compile(options)
            svg_files = sorted(tmpdir_path.glob(f"{constants.OUTPUT_FILE_STEM}*.svg"), key=rendered_sorted_key)
            self.update_svg_func([str(f) for f in svg_files], tmpdir=tmpdir)

        # For any item with this role we must do 2 things:
        #   1. Check to see if we should expand or collapse tree around item
        #   2. Check if subcategories and notes have been load. If not, load data and populate rows.
        elif item.data(constants.DIR_ROLE):
            loaded = item.data(constants.LOADED_ROLE)

            if loaded is False:
                cat: Category = item.data(constants.DIR_ROLE)
                self._load_item(item, cat)

            if self.tree.isExpanded(index):
                self.tree.collapse(index)
            else:
                self.tree.expand(index)

        elif item.data(constants.COURSE_CONTAINER_ROLE):
            if self.tree.isExpanded(index):
                self.tree.collapse(index)
            else:
                self.tree.expand(index)


    def _load_item(self, item: QStandardItem, cat: Category):
        # Check for placeholder row
        if (c1 := item.child(0)):
            if c1.text() == "placeholder":
                item.removeRow(0)

        for sub_cat in cat.children():
            sub_cat_item = QStandardItem(sub_cat.name)
            sub_cat_item.setData(sub_cat, constants.DIR_ROLE)
            sub_cat_item.setData(False, constants.LOADED_ROLE)
            sub_cat_item.appendRow(QStandardItem("placeholder"))

            item.appendRow(sub_cat_item)

        for note in cat.notes():
            note_item = QStandardItem(note.name)
            note_item.setData(note, constants.FILE_ROLE)
            item.appendRow(note_item)

        item.setData(True, constants.LOADED_ROLE)

    def populate_tree(self):
        if self.root_item is None:
            return

        courses = Courses(config)
        root_notes_item = QStandardItem(self.root_course_cat.name)
        root_course_item = QStandardItem("Courses")

        root_notes_item.setData(self.root_course_cat, constants.DIR_ROLE)
        root_notes_item.setData(False, constants.LOADED_ROLE)
        root_notes_item.appendRow(QStandardItem("placeholder"))

        root_course_item.setData(True, constants.COURSE_CONTAINER_ROLE)

        self.root_item.appendRow(root_notes_item)
        self.root_item.appendRow(root_course_item)

        for name, course in courses.courses.items():
            course_item = QStandardItem(name)
            course_item.setData(True, constants.COURSE_CONTAINER_ROLE)
            root_course_item.appendRow(course_item)
            if (main_file := course.typset_files["main"]) is not None:
                main_item = QStandardItem("main")
                main_item.setData(main_file, constants.FILE_ROLE)
                course_item.appendRow(main_item)

    def toggle_callback(self):
        pass

    def connect_toggle_button(self, callback: Callable[[], None]):
        self.toggle_button.clicked.connect(callback)

    # TODO how do I get note name?
    def connect_new_note(self, callback: Callable[[str, Category, FileType], None]):
        def wrapper():
            index = self.tree.currentIndex()
            item = self.model.itemFromIndex(index)
            if item is None:
                return
            if item.data(constants.FILE_ROLE) is not None:
                note = item.data(constants.FILE_ROLE)
                parent_cat = self.root_course_cat
                if isinstance(note, Note):
                    parent_cat = note.category
            text = index.data()
#            callback(parent_cat)
        self.new_note_button.clicked.connect(wrapper)

    def connect_new_cat(self, callback: Callable[[str, Optional[Category]], None]):
        def wrapper():
            index = self.tree.currentIndex()
            text = index.data()
            print(text)
        self.new_cat_button.clicked.connect(wrapper)

    def connect_doc_builder(self, builder_widget: QWidget):
        def callback(mode: str) -> None:
            if mode == "Preview":
                builder_widget.setHidden(True)
            else:
                builder_widget.setHidden(False)
        self.mode_selector.connect_mode_btn(callback)


class CollapsedNavBar(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.setFixedWidth(30)
        self.setLayout(self.main_layout)
        self.initUI()

    def initUI(self):
        self._create_widgets()
        self._configure_widgets()
        self._add_widgets()

    def _create_widgets(self):
        self.toggle_button = QPushButton('\u25B6')

    def _add_widgets(self):
        self.main_layout.addWidget(self.toggle_button, alignment=Qt.AlignmentFlag.AlignLeft)
        spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.main_layout.addSpacerItem(spacer)

    def _configure_widgets(self):
        self.toggle_button.setStyleSheet(TOGGLE_BUTTON_CSS)

    def connect_toggle_button(self, callback: Callable[[], None]):
        self.toggle_button.clicked.connect(callback)



class ModeSelector(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.btn_preview = QPushButton("Preview")
        self.btn_editor = QPushButton("Editor")
        self.btn_label = QLabel("Document Mode")
        main_layout = QVBoxLayout()
        btn_widget = QWidget()
        btn_layout = QHBoxLayout()

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        for btn in (self.btn_editor, self.btn_preview):
            btn.setCheckable(True)
            btn_layout.addWidget(btn)
            self.btn_group.addButton(btn)

        self.btn_preview.setChecked(True)
        btn_widget.setLayout(btn_layout)
        main_layout.addWidget(self.btn_label, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(btn_widget)
        self.setLayout(main_layout)

    def connect_mode_btn(self, callback: Callable[[str], None]):
        self.btn_group.buttonClicked.connect(lambda btn: callback(btn.text()))
