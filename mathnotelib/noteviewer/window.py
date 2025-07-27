import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional, Protocol

from PyQt6.QtGui import QBrush, QMouseEvent, QPalette, QStandardItem, QStandardItemModel, QTransform, QWheelEvent
from PyQt6.QtWidgets import (QApplication, QFrame, QGestureEvent, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QHBoxLayout, QMainWindow, QPinchGesture, QPushButton, QScrollArea, QSizePolicy,
                             QSpacerItem, QStyle, QStyleOptionViewItem, QToolBar, QTreeView, QVBoxLayout, QWidget)
from PyQt6.QtCore import QEvent, QFileSystemWatcher, QModelIndex, QProcess, QTimer, pyqtSignal, Qt
from PyQt6.QtSvgWidgets import QGraphicsSvgItem, QSvgWidget
from PyQt6 import QtCore


from .style import MAIN_WINDOW_CSS, SVG_VIEWER_CSS, TOGGLE_BUTTON_CSS, TREE_VIEW_CSS
from ..utils import config, rendered_sorted_key
from ..structure import NotesManager, Courses, Category, OutputFormat, TypsetCompileOptions, TypsetFile

ROOT_DIR = Path(config["root"])
VIEWER_SIZE = (800, 1000)

OUTPUT_FILE_STEM = "rendered"
TYP_FILE_LIVE = "/tmp/live.typ"
SVG_FILE_LIVE = "/tmp/live.svg"

FILE_ROLE = Qt.ItemDataRole.UserRole + 1
DIR_ROLE = Qt.ItemDataRole.UserRole + 2
LOADED_ROLE = Qt.ItemDataRole.UserRole + 3
COURSE_FILE_ROLE = Qt.ItemDataRole.UserRole + 4
COURSE_CONTAINER_ROLE = Qt.ItemDataRole.UserRole + 5

class UpdateSvgCallback(Protocol):
    def __call__(self, path: list[str], tmpdir: Optional[tempfile.TemporaryDirectory]) -> None:...

class ZMultiPageViewer(QGraphicsView):
    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        self.setBackgroundBrush(QBrush(Qt.GlobalColor.white))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._zoom: float = 1.0
        self._zoom_min: float = 1.0
        self._zoom_max: float = 5.0
        self._last_pinch_scale: float = 1.0
        self._y_offset: float = 0
        self._initial_batch_size: int = 5
        self._pending_items: list = []
        self._timer: QTimer = QTimer()
        self.target_width = 800
        self.target_height = 1000
        self.tmpdir: Optional[tempfile.TemporaryDirectory] = None

    def load(self, svg_paths: list[str] | str, tmpdir: tempfile.TemporaryDirectory | None):
        self._scene.clear()
        self.reset_zoom()
        self._y_offset = 0
        self.tmpdir = tmpdir
        paths = svg_paths if isinstance(svg_paths, list) else [svg_paths]
        load_num = min(len(paths), self._initial_batch_size)
        for path in paths[:load_num]:
            self.append_item(path)

        if len(paths) > self._initial_batch_size:
            self._pending_items = paths[self._initial_batch_size:]
            self._timer.timeout.connect(self._load_pending)
            self._timer.start(30)

    def _load_pending(self):
        if len(self._pending_items) == 0:
            self._timer.stop()
            if self.tmpdir:
                self.tmpdir.cleanup()
                self.tmpdir = None
            return
        item = self._pending_items.pop(0)
        self.append_item(item)

    def append_item(self, path: str):
        if len(items := self._scene.items()) > 0:
            prev_item = items[-1]
            prev_bounds = prev_item.boundingRect()
            prev_scale_y = self.target_height / prev_bounds.height()
            self._y_offset += 20 * prev_scale_y

        item = QGraphicsSvgItem(path)
        item.setPos(0, self._y_offset)

        bounds = item.boundingRect()
        scale_x = self.target_width / bounds.width()
        scale_y = self.target_height / bounds.height()
        item.setTransform(QTransform().scale(scale_x, scale_y))
        self._y_offset += scale_y * bounds.height()

        self._scene.addItem(item)
        self._scene.setSceneRect(0, 0, self.target_width, self._y_offset)

    def event(self, event: Optional[QtCore.QEvent]) -> bool:
        if event is None: return False
        if event.type() == QEvent.Type.NativeGesture.value:
            return self.native_gesture_event(event)
        return super().event(event)

    def scale_view(self, factor):
        new_zoom = self._zoom * factor
        if new_zoom < self._zoom_min:
            factor = self._zoom_min / self._zoom
            new_zoom = self._zoom_min
        elif new_zoom > self._zoom_max:
            factor = self._zoom_max / self._zoom
            new_zoom = self._zoom_max
        self.scale(factor, factor)
        self._zoom = new_zoom

    def native_gesture_event(self, event):
        gesture_type = event.gestureType()
        if gesture_type.value == 3:
            delta = event.value()
            scale_factor = 1.0 + delta
            self.scale_view(scale_factor)
            return True
        return False

    def gestureEvent(self, event: QGestureEvent):
        pinch = event.gesture(Qt.GestureType.PinchGesture)
        if isinstance(pinch, QPinchGesture):
            self.handle_pinch(pinch)
            return True
        return False

    def handle_pinch(self, pinch: QPinchGesture):
        if pinch.state() == Qt.GestureState.GestureStarted:
            self._last_pinch_scale = 1.0
        elif pinch.state() == Qt.GestureState.GestureUpdated:
            current = pinch.scaleFactor()
            delta = current / max(self._last_pinch_scale, 0.1)
            self.scale(delta, delta)
            self._last_pinch_scale = current

    def reset_zoom(self):
        self.resetTransform()
        self._zoom = 1

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
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)
        self.setFixedWidth(200)

        self.initUI()

    def initUI(self):
        self._create_widgets()
        self._configure_widgets()
        self._add_widgets()
        self.populate_tree()

    def _create_widgets(self):
        self.toggle_button = QPushButton("x")
        self.menu_bar_layout = QHBoxLayout()
        self.model = QStandardItemModel()
        self.tree = QTreeView()
        self.root_item = self.model.invisibleRootItem()

    def _configure_widgets(self):
        self.toggle_button.setStyleSheet(TOGGLE_BUTTON_CSS)
        self.toggle_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.toggle_button.clicked.connect(self.toggle_tree)

        self.tree.setModel(self.model)
        self.tree.setFrameShape(QFrame.Shape.NoFrame)
        self.tree.header().hide() #TODO: don't think header() every returns None..
        self.tree.expanded.connect(self._expand_callback)
        self.tree.setStyleSheet(TREE_VIEW_CSS)
        self.tree.clicked.connect(self._item_clicked_callback)

    def _add_widgets(self):
        self.menu_bar_layout.addWidget(self.toggle_button)
#        self.hidden_layout.setFixedWidth(40)
        self.menu_bar_layout.addSpacerItem(QSpacerItem(15, 15, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        self.main_layout.addLayout(self.menu_bar_layout)
        self.main_layout.addWidget(self.tree)

    def _expand_callback(self, index: QModelIndex):
        # Remark: the item will originally expand with the placeholder element. Once this occurs
        # we will remove placeholder and populate with correct options. This could give rise to a bug where placeholder persists
        item = self.model.itemFromIndex(index)
        if item is None:
            return
        cat = item.data(DIR_ROLE)
        loaded = item.data(LOADED_ROLE)
        if cat is not None and loaded is not None:
            if loaded is False:
                self._load_item(item, cat)

    # How do I deal with courses?
    # TODO add lazy compile - check if pdf exists
    # TODO compile in batches
    def _item_clicked_callback(self, index: QModelIndex):

        item = self.model.itemFromIndex(index)
        if item is None:
            return

        # TODO: handle failed compilation
        if item.data(FILE_ROLE) is not None:

            file: TypsetFile = item.data(FILE_ROLE)
            tmpdir = tempfile.TemporaryDirectory()
            tmpdir_path = Path(tmpdir.name)

            options = TypsetCompileOptions(file.path, OutputFormat.SVG, multi_page=True)
            options.set_output_dir(tmpdir_path)
            options.set_output_file_stem(OUTPUT_FILE_STEM)

            return_code = file.compile(options)
            svg_files = sorted(tmpdir_path.glob(f"{OUTPUT_FILE_STEM}*.svg"), key=rendered_sorted_key)
            self.update_svg_func([str(f) for f in svg_files], tmpdir=tmpdir)


        # For any item with this role we must do 2 things:
        #   1. Check to see if we should expand or collapse tree around item
        #   2. Check if subcategories and notes have been load. If not, load data and populate rows.
        elif item.data(DIR_ROLE):
            loaded = item.data(LOADED_ROLE)

            if loaded is False:
                cat: Category = item.data(DIR_ROLE)
                self._load_item(item, cat)

            if self.tree.isExpanded(index):
                self.tree.collapse(index)
            else:
                self.tree.expand(index)

        elif item.data(COURSE_CONTAINER_ROLE):
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
            sub_cat_item.setData(sub_cat, DIR_ROLE)
            sub_cat_item.setData(False, LOADED_ROLE)
            sub_cat_item.appendRow(QStandardItem("placeholder"))

            item.appendRow(sub_cat_item)

        for note in cat.notes():
            note_item = QStandardItem(note.name)
            note_item.setData(note, FILE_ROLE)
            item.appendRow(note_item)

        item.setData(True, LOADED_ROLE)

    def populate_tree(self):
        if self.root_item is None: return
        notes_dir = ROOT_DIR / "Notes"
        root_cat = NotesManager.build_root_category(notes_dir)
        courses = Courses(config)

        root_notes_item = QStandardItem(root_cat.name)
        root_course_item = QStandardItem("Courses")

        root_notes_item.setData(root_cat, DIR_ROLE)
        root_notes_item.setData(False, LOADED_ROLE)
        root_notes_item.appendRow(QStandardItem("placeholder"))

        root_course_item.setData(True, COURSE_CONTAINER_ROLE)

        self.root_item.appendRow(root_notes_item)
        self.root_item.appendRow(root_course_item)

        for name, course in courses.courses.items():
            course_item = QStandardItem(name)
            course_item.setData(True, COURSE_CONTAINER_ROLE)
            root_course_item.appendRow(course_item)
            if (main_file := course.typset_files["main"]) is not None:
                main_item = QStandardItem("main")
                main_item.setData(main_file, FILE_ROLE)
                course_item.appendRow(main_item)

    def toggle_tree(self):
        self.tree_visible = not self.tree_visible
#        self.tree.setVisible(self.tree_visible)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.widget = QWidget()
        self.main_layout = QHBoxLayout(self.widget)
        self.setCentralWidget(self.widget)
        self.setContentsMargins(0, 0, 0, 0)
        self.initUi()

        # TODO
#        self.compile_typst(TYP_FILE_LIVE)
        self.watcher.addPath(TYP_FILE_LIVE)

    def initUi(self):
        self._create_widgets()
        self._configure_widgets()
        self._add_widgets()

    def _create_widgets(self):
        self.toolbar = QToolBar()
        self.viewer = ZMultiPageViewer()
        self.watcher = QFileSystemWatcher()
        self.nav_bar = Navbar(self.update_svg)

    def _configure_widgets(self):
        self.setStyleSheet(MAIN_WINDOW_CSS)
        self.viewer.setFixedSize(800, 1000)
        self.watcher.fileChanged.connect(self.on_typ_changed)

    def _add_widgets(self):
        self.addToolBar(self.toolbar)
        self.main_layout.addWidget(self.nav_bar, alignment=Qt.AlignmentFlag.AlignLeft)
        self.main_layout.addWidget(self.viewer, alignment=Qt.AlignmentFlag.AlignCenter)

    def on_typ_changed(self):
        self.watcher.removePath(TYP_FILE_LIVE)
        self.watcher.addPath(TYP_FILE_LIVE)
        self.compile_typst(TYP_FILE_LIVE)

    def compile_typst(self, path: str):
        self.process = QProcess()
        self.process.start("typst", ["compile", path, "--format", "svg"])
        self.process.finished.connect(lambda : self.update_svg(path))

    def update_svg(self, path: str | list[str], tmpdir: Optional[tempfile.TemporaryDirectory] = None):
        paths = path if isinstance(path, list) else [path]
        if all(Path(p).exists() for p in paths):
            self.viewer.load(path, tmpdir=tmpdir)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
