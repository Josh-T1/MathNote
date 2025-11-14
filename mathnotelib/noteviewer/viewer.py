import tempfile
from typing import Callable

from PyQt6.QtGui import QBrush, QIcon, QMouseEvent, QTransform, QWheelEvent
from PyQt6.QtWidgets import (QWIDGETSIZE_MAX, QApplication, QFrame, QGestureEvent, QGraphicsScene, QGraphicsView, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QMainWindow, QPinchGesture, QPushButton, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget)
from PyQt6.QtCore import QEvent, QFileSystemWatcher, QModelIndex, QProcess, QSize, QTimer, pyqtSignal, Qt
from PyQt6.QtSvgWidgets import QGraphicsSvgItem, QSvgWidget
from PyQt6 import QtCore

from .style import CLOSE_TAB_BTN_CSS, ICON_CSS, PAGE_INPUT_CSS, TAB_BTN_CSS, TAB_BTN_EMPTY_CSS, TAB_WIDGET_CSS
from . import constants

class ZMultiPageViewer(QGraphicsView):
    EDGE_THRESHOLD = 20
    MAX_ZOOM = 5.0
    MIN_ZOOM = 1.0
    BATCH_SIZE = 5

    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        self.setStyleSheet("background-color: transparent;")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setContentsMargins(0, 0, 0, 0)
        self.setMouseTracking(True)

        self._zoom = 1.0
        self._last_pinch_scale: float = 1.0
        self._y_offset = 0.0
        self._timer = QTimer()
        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_scrollbars)
        self._restore_data = None
        self._pending_items: list = []
        self.tmpdir: tempfile.TemporaryDirectory | None = None

    def _restore(self):
        if self._restore_data is None:
            return
        self._zoom = self._restore_data["zoom"]
        self.setTransform(self._restore_data["transform"])
        if (hbar := self.horizontalScrollBar()) is not None:
            hbar.setValue(self._restore_data["scroll_pos"][0])
        if (vbar := self.verticalScrollBar()) is not None:
            vbar.setValue(self._restore_data["scroll_pos"][1])
        self._restore_data = None

    def _set_restore_vals(self):
        h_val, v_val = 0, 0 # does this make sense?
        if (hscroll_bar := self.horizontalScrollBar()) is not None:
            h_val = hscroll_bar.value()
        if (vscroll_bar := self.verticalScrollBar()) is not None:
            v_val = vscroll_bar.value()
        self._restore_data = {
                "zoom": self._zoom,
                "scroll_pos": (h_val, v_val),
                "transform": self.transform()
                }

    def _create_overlay(self):
        # TODO: finish
        self.page_input = QLineEdit(self)
#        self.page_input.setWindowFlags(self.page_input.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.page_input.setFixedSize(QSize(80, 30))
        self.page_input.setStyleSheet(PAGE_INPUT_CSS)
        self.page_input.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.page_input.returnPressed.connect(self._jump_to_page)
        x, y = (constants.VIEWER_WIDTH - self.page_input.width()) // 2, 2
        self.page_input.move(x, y)

    def _jump_to_page(self):
        pass

    def wheelEvent(self, event: QWheelEvent | None) -> None:
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._hide_timer.start(1500)
        super().wheelEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:
        viewport = self.viewport()
        if event is None or viewport is None:
            return
        pos = event.pos()
        x, y = viewport.width(), viewport.height()
        near_right = self.EDGE_THRESHOLD > abs(pos.x() - x)
        near_bottom = self.EDGE_THRESHOLD > abs(pos.y() - y)

        if near_right or near_bottom:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self._hide_timer.start(1500)
        super().mouseMoveEvent(event)

    def _hide_scrollbars(self):
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def load(self,
             svg_paths: list[str] | str,
             tmpdir: tempfile.TemporaryDirectory | None,
             preserve_state: bool=False,
             ):
        if preserve_state:
            self._set_restore_vals()
        self._scene.clear()
        self.reset_zoom()
        self._y_offset = 0
        self.tmpdir = tmpdir
        paths = svg_paths if isinstance(svg_paths, list) else [svg_paths]
        for path in paths:
            self.append_item(path)
        if preserve_state:
#            QTimer.singleShot(10, lambda: self._restore())
            self._restore()




#    def _load_pending(self):
#        if len(self._pending_items) == 0:
#            self._timer.stop()
#            if self.tmpdir:
#                self.tmpdir.cleanup()
#                self.tmpdir = None
#            return
#        item = self._pending_items.pop(0)
#        self.append_item(item)

    def append_item(self, path: str):
        if len(items := self._scene.items()) > 0:
            prev_item = items[-1]
            prev_bounds = prev_item.boundingRect()
            prev_scale_y = constants.VIEWER_HEIGHT / prev_bounds.height()
#            self._y_offset += 10 * prev_scale_y

        item = QGraphicsSvgItem(path)
        item.setPos(0, self._y_offset)

        bounds = item.boundingRect()
        scale_x = constants.VIEWER_WIDTH / bounds.width()
        scale_y = constants.VIEWER_HEIGHT / bounds.height()
        item.setTransform(QTransform().scale(scale_x, scale_y))
        self._y_offset += scale_y * bounds.height()

        self._scene.addItem(item)
        self._scene.setSceneRect(0, 0, constants.VIEWER_WIDTH, self._y_offset)

    def event(self, event: QtCore.QEvent | None) -> bool:
        if event is None: return False
        if event.type() == QEvent.Type.NativeGesture.value:
            return self.native_gesture_event(event)
        return super().event(event)

    def scale_view(self, factor):
        new_zoom = self._zoom * factor
        if new_zoom < self.MIN_ZOOM:
            factor = self.MIN_ZOOM / self._zoom
            new_zoom = self.MIN_ZOOM
        elif new_zoom > self.MAX_ZOOM:
            factor = self.MAX_ZOOM / self._zoom
            new_zoom = self.MAX_ZOOM
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


class ToolTabBar(QWidget):
    def __init__(self):
        super().__init__()
        self.toolbar = self.build_tool_bar()
        self.main_layout = QHBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.main_layout.setSpacing(2)
        self.main_layout.addWidget(self.toolbar)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)
        self.setFixedHeight(30)

    def build_tool_bar(self) -> QWidget:
        cont = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.setContentsMargins(0, 0, 0, 0)
        cont.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        cont.setLayout(layout)
        self.add_tab_btn = QPushButton()
        self.add_tab_btn.setToolTip("New Tab")
        self.add_tab_btn.setIcon(QIcon(str(constants.ICON_PATH / "add.png")))
        self.add_tab_btn.setFixedSize(constants.ICON_SIZE)
        self.add_tab_btn.setStyleSheet(ICON_CSS)
        layout.addWidget(self.add_tab_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        return cont

    def add_tab_button(self, label: str, switch_callback: Callable[[], None], close_callback: Callable[[], None]) -> None:
        cont = QWidget()
        cont.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        def wrapped_close():
            cont.deleteLater()
            self.main_layout.removeWidget(cont)
            close_callback()

        layout = QHBoxLayout(cont)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        tab_btn = QPushButton(label)
        tab_btn.setFlat(True)
        tab_btn.setFixedHeight(30)
        tab_btn.setMinimumWidth(70)
        tab_btn.setMaximumWidth(120)
        tab_btn.clicked.connect(switch_callback)
        tab_btn.setStyleSheet(TAB_BTN_EMPTY_CSS)
        close_btn = QPushButton()
        close_btn.setFixedSize(QSize(20, 20))
        close_btn.setIcon(QIcon(str(constants.ICON_PATH / "exit.png")))
        close_btn.setStyleSheet(CLOSE_TAB_BTN_CSS)
        close_btn.clicked.connect(wrapped_close)
        cont.setStyleSheet(TAB_WIDGET_CSS)

        layout.addWidget(tab_btn)
        layout.addWidget(close_btn)
        count = self.main_layout.count()
        self.main_layout.insertWidget(max(0, count - 1), cont)

    def connect_tab_btn(self, callback: Callable[[], None]):
        self.add_tab_btn.clicked.connect(callback)

    def focus_tab(self, idx: int):
        # TODO remove for loop
        for i in range(self.main_layout.count()): # -1 to account for settings widget in toolbar
            item = self.main_layout.itemAt(i)
            if item is None:
                return
            tab = item.widget()
            if tab is None:
                return
            if i == idx:
                tab.setStyleSheet("background-color: #555;")
            else:
                tab.setStyleSheet("background-color: transparent;")


class TabbedSvgViewer(QWidget):
    def __init__(self, parent: QWidget | None=None):
        super().__init__(parent)
        self.initUI()
        self.max_tabs = 5

    def initUI(self):
        # Layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)
        self.setContentsMargins(0, 0, 0, 0)
        # Create widgets
        self.tab_bar = ToolTabBar()
        self.stack = QStackedWidget()
        # Configure widgets
        self.tab_bar.connect_tab_btn(lambda: self.add_svg_tab(focus=True))
        self.stack.setStyleSheet("background-color: white;")
        self.stack.setFixedSize(constants.VIEWER_WIDTH, constants.VIEWER_HEIGHT)
        self.stack.setContentsMargins(0, 0, 0, 0)
        # Add widgets to layout
        self.main_layout.addWidget(self.tab_bar)
        self.main_layout.addWidget(self.stack)

    def close_tab(self, widget: QWidget):
        idx = self.stack.indexOf(widget)
        if idx == -1: # widget is not in stack
            return
        self.stack.removeWidget(widget)
        widget.deleteLater()
        if self.stack.count() == 0:
            self.add_svg_tab(focus=True)
#                self.tab_bar.focus_tab()
        else:
            next_idx = idx if self.stack.count() -1 >= idx else self.stack.count()- 1
            self.stack.setCurrentIndex(next_idx)
            self.tab_bar.focus_tab(next_idx)

    def change_tab(self, widget: QWidget):
        idx = self.stack.indexOf(widget)
        self.stack.setCurrentIndex(idx)
        self.tab_bar.focus_tab(idx)

    def addTab(self, widget: QWidget, label: str, focus: bool=True):
        if self.max_tabs == self.stack.count():
            return
        change = lambda: self.change_tab(widget)
        close = lambda: self.close_tab(widget)
        self.stack.addWidget(widget)
        self.tab_bar.add_tab_button(label, change, close)
        # First tab should auto focus
        if self.stack.count() == 1 or focus:
            self.change_tab(widget)

    def add_svg_tab(self, focus: bool=True):
        view = ZMultiPageViewer()
        view.setFixedSize(constants.VIEWER_WIDTH, constants.VIEWER_HEIGHT)
        self.addTab(view, f"{self.stack.count() + 1}", focus=focus)


    def load_current_viewer(self,
                            svg_paths: list[str] | str,
                            tmpdir: tempfile.TemporaryDirectory | None=None,
                            name: str | None=None,
                            preserve_state: bool=False
                            ):
        current_viewer = self.stack.currentWidget()
        if not isinstance(current_viewer, ZMultiPageViewer):
            return
        current_viewer.load(svg_paths, tmpdir, preserve_state=preserve_state)
        idx = self.stack.indexOf(current_viewer)
        if name is None:
            return
        try:
            widget = self.tab_bar.main_layout.itemAt(idx).widget()
            btn = widget.layout().itemAt(0).widget()
            if isinstance(btn, QPushButton):
                btn.setText(name)
                btn.setToolTip(name)
                btn.setStyleSheet(TAB_BTN_CSS)
        except Exception as e:
            pass


class SettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setFixedSize(constants.VIEWER_WIDTH, constants.VIEWER_HEIGHT)
        self.setLayout(main_layout)
        self.setStyleSheet("background-color: #282828;")

        self.title = QLabel("Settings")
        spacer = QWidget()

        self.title.setStyleSheet("font-size: 24px;")
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        main_layout.addWidget(self.title, alignment=Qt.AlignmentFlag.AlignTop)
        main_layout.addWidget(spacer)
