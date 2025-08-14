import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional, Protocol

from PyQt6.QtGui import QBrush, QTransform
from PyQt6.QtWidgets import (QApplication, QFrame, QGestureEvent, QGraphicsScene, QGraphicsView, QHBoxLayout,
                             QLabel, QListWidget, QMainWindow, QPinchGesture, QToolBar, QTreeView, QVBoxLayout, QWidget)
from PyQt6.QtCore import QEvent, QFileSystemWatcher, QModelIndex, QProcess, QTimer, pyqtSignal, Qt
from PyQt6.QtSvgWidgets import QGraphicsSvgItem, QSvgWidget
from PyQt6 import QtCore

from .navbar import Navbar, CollapsedNavBar, ModeSelector
from .builder_widget import DocumentBuilder
from . import constants
from .style import MAIN_WINDOW_CSS
from ..utils import FileType, config, rendered_sorted_key
from ..structure import NotesManager, Courses, Category


class ZMultiPageViewer(QGraphicsView):
    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        self.setBackgroundBrush(QBrush(Qt.GlobalColor.white))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setContentsMargins(0, 0, 0, 0)

        self.target_width = 800
        self.target_height = 1000
        self._zoom: float = 1.0
        self._zoom_min: float = 1.0
        self._zoom_max: float = 5.0
        self._last_pinch_scale: float = 1.0
        self._y_offset: float = 0
        self._timer: QTimer = QTimer()

        self._initial_batch_size: int = 5
        self._pending_items: list = []
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.notes_manager = NotesManager(Path(config["root"]) / "Notes")
        self.widget = QWidget()
        self.main_layout = QHBoxLayout(self.widget)
        self.setCentralWidget(self.widget)
        self.setContentsMargins(0, 0, 0, 0)
        self.initUi()
        self.main_layout.setSpacing(0)
        # TODO
#        self.compile_typst(TYP_FILE_LIVE)
        self.watcher.addPath(constants.TYP_FILE_LIVE)

        self._nav_minimal: bool = False

    def initUi(self):
        self._create_widgets()
        self._configure_widgets()
        self._add_widgets()

    def _create_widgets(self):
        self.toolbar = QToolBar()
        self.viewer = ZMultiPageViewer()
        self.watcher = QFileSystemWatcher()
        self.nav_bar = Navbar(self.update_svg)
        self.minimal_nav_bar = CollapsedNavBar()
        self.doc_builder_widget = DocumentBuilder()

    def _configure_widgets(self):
        self.setStyleSheet(MAIN_WINDOW_CSS)
        self.viewer.setFixedSize(800, 1000)
        self.watcher.fileChanged.connect(self.on_typ_changed)
        self.minimal_nav_bar.connect_toggle_button(self._toggle_nav_callback)
        self.nav_bar.connect_toggle_button(self._toggle_nav_callback)
        self.nav_bar.connect_new_note(self._new_note_callback)
        self.nav_bar.connect_new_cat(self._new_cat_callback)
        self.nav_bar.connect_doc_builder(self.doc_builder_widget)
        self.doc_builder_widget.setFixedWidth(200)
        self.doc_builder_widget.setHidden(True)

    def _add_widgets(self):
        self.addToolBar(self.toolbar)
        self.main_layout.addWidget(self.nav_bar, alignment=Qt.AlignmentFlag.AlignLeft)
#        self.main_layout.addWidget(self.minimal_nav_bar, alignment=Qt.AlignmentFlag.AlignLeft)
        self.main_layout.addWidget(self.viewer, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.doc_builder_widget, alignment=Qt.AlignmentFlag.AlignRight)

    def on_typ_changed(self):
        self.watcher.removePath(constants.TYP_FILE_LIVE)
        self.watcher.addPath(constants.TYP_FILE_LIVE)
        self.compile_typst(constants.TYP_FILE_LIVE)

    def compile_typst(self, path: str):
        self.process = QProcess()
        self.process.start("typst", ["compile", path, "--format", "svg"])
        self.process.finished.connect(lambda : self.update_svg(path))

    def update_svg(self, path: str | list[str], tmpdir: Optional[tempfile.TemporaryDirectory] = None):
        paths = path if isinstance(path, list) else [path]
        if all(Path(p).exists() for p in paths):
            self.viewer.load(path, tmpdir=tmpdir)

    def _toggle_nav_callback(self):
        self._nav_minimal = not self._nav_minimal
        if self._nav_minimal:
            self.main_layout.removeWidget(self.nav_bar)
            self.nav_bar.setParent(None)
            self.main_layout.insertWidget(0, self.minimal_nav_bar)
        else:
            self.main_layout.removeWidget(self.minimal_nav_bar)
            self.minimal_nav_bar.setParent(None)
            self.main_layout.insertWidget(0, self.nav_bar)

    def _new_note_callback(self, name: str, cat: Category, note_type: FileType):
#        self.notes_manager.new_note(name,cat, note_type)
        print(name, cat, note_type)

    def _new_cat_callback(self, name: str, cat: Optional[Category] = None):
        print(name, cat)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
