import tempfile
from typing import Callable
from functools import partial

from PyQt6.QtGui import QIcon, QMouseEvent, QTransform, QWheelEvent
from PyQt6.QtWidgets import (QGestureEvent, QGraphicsScene, QGraphicsView, QHBoxLayout,
                            QLineEdit, QPinchGesture, QPushButton, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget)
from PyQt6.QtCore import QEvent, QSize, QTimer, pyqtSignal, Qt
from PyQt6.QtSvgWidgets import QGraphicsSvgItem
from PyQt6 import QtCore

from .style import CLOSE_TAB_BTN_CSS, COLOR_BACKGROUND_ALT, COLOR_FOCUSED, COLOR_FOCUSED_BORDER, COLOR_TEXT_PRIMARY, ICON_CSS, PAGE_INPUT_CSS, TAB_BTN_EMPTY_CSS
from .constants import VIEWER_WIDTH, VIEWER_HEIGHT, ICON_PATH, ICON_SIZE
from ..models import Assignment, Lecture, SourceFile


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

        # Wtf is this doing here?
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
#        self.page_input.returnPressed.connect(self._jump_to_page)
        x, y = (VIEWER_WIDTH - self.page_input.width()) // 2, 2
        self.page_input.move(x, y)

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
            self._scene.items().clear() # TODO Change
            self.append_item(path)
        if preserve_state:
#            QTimer.singleShot(10, lambda: self._restore())
            self._restore()


    def append_item(self, path: str):
        if len(items := self._scene.items()) > 0:
            prev_item = items[-1]
            prev_bounds = prev_item.boundingRect()
            prev_scale_y = VIEWER_HEIGHT / prev_bounds.height()
#            self._y_offset += 10 * prev_scale_y

        item = QGraphicsSvgItem(path)
        item.setPos(0, self._y_offset)

        bounds = item.boundingRect()
        scale_x = VIEWER_WIDTH / bounds.width()
        scale_y = VIEWER_HEIGHT / bounds.height()
        item.setTransform(QTransform().scale(scale_x, scale_y))
        self._y_offset += scale_y * bounds.height()

        self._scene.addItem(item)
        self._scene.setSceneRect(0, 0, VIEWER_WIDTH, self._y_offset)

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

# WHy does it feel like changing tabs re compiles file?
class TabWidget(QWidget):
    def __init__(self, label: str,
                 switch_callback: Callable[[], None],
                 close_callback: Callable[["TabWidget"], None],
                 source: SourceFile | None = None,
                 parent=None,
                 ) -> None:
        super().__init__(parent)
        # By default QWidget are automatically painted and instances of classes subclassing QWidget do not have autoamatic painting
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.is_live = False
        self.is_focused = False
        self.label = label
        self.close_callback = close_callback
        self.switch_callback = switch_callback
        self.source_file = source
        self.initUi()

    def initUi(self):
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setContentsMargins(0, 0, 0, 0)

        main_layout = QHBoxLayout(self)
        col0_layout = QVBoxLayout()
        col1_layout = QVBoxLayout()
        col2_layout = QVBoxLayout()

        main_layout.addLayout(col0_layout)
        main_layout.addLayout(col1_layout)
        main_layout.addLayout(col2_layout)

        main_layout.setContentsMargins(0, 0, 0, 0)
        col0_layout.setContentsMargins(4, 4, 0, 0)
        col1_layout.setContentsMargins(0, 0, 0, 0)
        col2_layout.setContentsMargins(0, 0, 0, 0)

        main_layout.setSpacing(0)
        col0_layout.setSpacing(0)
        col1_layout.setSpacing(0)
        col2_layout.setSpacing(0)

        col0_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        col1_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        col2_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.tab_btn = QPushButton(self.label)
        self.tab_btn.setFlat(True)
        self.tab_btn.setFixedHeight(29)
        self.tab_btn.setMinimumWidth(69)
        self.tab_btn.setMaximumWidth(119)
        self.tab_btn.clicked.connect(self.switch_callback)
        self.tab_btn.setStyleSheet(TAB_BTN_EMPTY_CSS)


        close_btn = QPushButton()
        close_btn.setFixedSize(QSize(19, 20))
        close_btn.setIcon(QIcon(str(ICON_PATH / "exit.png")))
        close_btn.setStyleSheet(CLOSE_TAB_BTN_CSS)

        close_btn.clicked.connect(
                lambda: self.close_callback(self)
                )

        col1_layout.addWidget(self.tab_btn)
        col2_layout.addWidget(close_btn)

    def make_style_sheet(self) -> str:
        outline = f"1px solid {COLOR_TEXT_PRIMARY}" if self.is_live else f"1px solid {COLOR_FOCUSED_BORDER}"
        background_color = COLOR_FOCUSED if self.is_focused else COLOR_BACKGROUND_ALT

        return f"""
        border-top: {outline};
        border-left: {outline};
        border-right: {outline};
        border-bottom: none;
        background-color: {background_color};
        """


    def toggle_live(self):
        self.is_live = not self.is_live
        if self.is_live is False:
            self.setStyleSheet(self.make_style_sheet())
        else:
            self.setStyleSheet(self.make_style_sheet())

    def set_focus(self, focus=True):
        self.is_focused = focus
        if self.is_focused:
            self.setStyleSheet(self.make_style_sheet())
        else:
            self.setStyleSheet(self.make_style_sheet())


class ToolTabBar(QWidget):
    preview = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.toolbar = self.build_tool_bar()
        self.main_layout = QHBoxLayout()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.toolbar)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)
        self.setFixedHeight(30)


    def build_tool_bar(self) -> QWidget:
        cont = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.setContentsMargins(0, 0, 0, 0)
        cont.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        cont.setLayout(layout)
        self.live_preview_btn = QPushButton()
        self.live_preview_btn.setToolTip("Live Preview")
        self.live_preview_btn.setIcon(QIcon(str(ICON_PATH / "preview.png")))
        self.live_preview_btn.setFixedSize(QSize(ICON_SIZE))
        self.live_preview_btn.setStyleSheet(ICON_CSS)

        self.add_tab_btn = QPushButton()
        self.add_tab_btn.setToolTip("New Tab")
        self.add_tab_btn.setIcon(QIcon(str(ICON_PATH / "add.png")))
        self.add_tab_btn.setFixedSize(ICON_SIZE)
        self.add_tab_btn.setStyleSheet(ICON_CSS)

        layout.addWidget(self.add_tab_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.live_preview_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.live_preview_btn.clicked.connect(lambda: self.preview.emit())
        return cont

    def get_tabs(self) -> list[TabWidget]:
        tabs = []
        for i in range(self.main_layout.count()):
            item = self.main_layout.itemAt(i)

            if item is None:
                continue
            tab = item.widget()
            if isinstance(tab, TabWidget):
                tabs.append(tab)

        return tabs

    def get_focused_tab(self) -> TabWidget | None:
        tabs = self.get_tabs()
        for tab in tabs:
            if tab.is_focused:
                return tab
        return None

    def toggle_live(self) -> None:
        for i in range(self.main_layout.count()): # -1 to account for settings widget in toolbar
            item = self.main_layout.itemAt(i)

            if item is None: return
            tab = item.widget()
            if not isinstance(tab, TabWidget):
                return

            if tab.is_focused and tab.source_file is not None:
                tab.toggle_live()


    def focus_tab(self, idx: int):
        # TODO remove for loop
        curr_tab_idx = -1
        for i in range(self.main_layout.count()): # -1 to account for settings widget in toolbar
            item = self.main_layout.itemAt(i)
            if item is None:
                return
            tab = item.widget()
            if not isinstance(tab, TabWidget):
                return

            curr_tab_idx += 1
            if curr_tab_idx == idx:
                tab.set_focus(focus=True)
            else:
                tab.set_focus(focus=False)



class TabbedSvgViewer(QWidget):
    tab_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.initUI()
        self.max_tabs = 7 #set this dynamically based on min window size and tab size

    def initUI(self):
        # Layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.setLayout(self.main_layout)
        self.setContentsMargins(0, 0, 0, 0)

        # Create widgets
        self.tab_bar = ToolTabBar()
        self.stack = QStackedWidget()
        # Configure widgets
        self.setMinimumSize(VIEWER_WIDTH, VIEWER_HEIGHT)
        self.tab_bar.add_tab_btn.clicked.connect(lambda: self.addTab(focus=True))
        self.stack.setStyleSheet("background-color: white;")
        self.stack.setContentsMargins(0, 0, 0, 0)
        # Add widgets to layout
        self.main_layout.addWidget(self.tab_bar)
        self.main_layout.addWidget(self.stack)


    def close_tab(self, widget: QWidget, tab_widget: TabWidget):
        self.tab_bar.main_layout.removeWidget(tab_widget)
        tab_widget.deleteLater()

        idx = self.stack.indexOf(widget)
        largest_idx = self.stack.count() -1
        if idx == -1: # widget is not in stack
            return

        if self.stack.count() == 1:
            self.stack.removeWidget(widget)
            self.addTab(focus=False)
            self.tab_bar.focus_tab(0)

        elif self.stack.count() > 1 and tab_widget.is_focused:
            next_idx = idx + 1 if largest_idx > idx else idx - 1
            self.stack.setCurrentIndex(next_idx)
            self.stack.removeWidget(widget)
            self.tab_bar.focus_tab(next_idx)
        else:
            self.stack.removeWidget(widget)

        widget.deleteLater()

    def change_tab(self, widget: QWidget):
        idx = self.stack.indexOf(widget)
        self.stack.setCurrentIndex(idx)
        self.tab_bar.focus_tab(idx)
        self.tab_changed.emit()

    # exchange label: str for path: str
    def addTab(self, source: SourceFile | None = None, focus: bool=True):
        """
        Params:
            - label: displayed on tab widget
            - focus: if set to true tab widget is highlighted and set to 'focus' (live preview uses the focus property, see LiveTypstPreview)
        """
        view = ZMultiPageViewer()
        view.setMinimumSize(VIEWER_WIDTH, VIEWER_HEIGHT)
#        label = label if label is not None else f"{self.stack.count() + 1}"
        if isinstance(source, Lecture) or isinstance(source, Assignment):
            func = getattr(source, "pretty_name", lambda: source.name)
            file_name = func()
        elif source is None:
            widgets = {int(tab.label) for tab in self.tab_bar.get_tabs() if tab.label.isdigit()}.union({0})
            file_name = f"{max(widgets) + 1}"
        else:
            file_name = source.path.parent.parent.stem

        if self.max_tabs == self.stack.count():
            return

        close_callback = partial(self.close_tab, view)
        switch_callback = partial(self.change_tab, view)
        self.stack.addWidget(view)
        # partial is destroying type hint... hopefully that is the only issue here
        tab = TabWidget(file_name, switch_callback, close_callback)
        count = self.tab_bar.main_layout.count()
        self.tab_bar.main_layout.insertWidget(max(0, count - 1), tab)

        # First tab should auto focus
        if self.stack.count() == 1:
            self.stack.setCurrentWidget(view)
            self.tab_bar.focus_tab(0)

        elif self.stack.count() > 1 and focus:
            self.change_tab(view)


    def load_current_viewer(self,
                            svg_paths: list[str] | str,
                            tmpdir: tempfile.TemporaryDirectory | None=None,
                            source: SourceFile | None=None,
                            preserve_state: bool=False
                            ):
        current_viewer = self.stack.currentWidget()
        if not isinstance(current_viewer, ZMultiPageViewer):
            return
        current_viewer.load(svg_paths, tmpdir, preserve_state=preserve_state)

        focused_tab = self.tab_bar.get_focused_tab()
        if focused_tab is None or source is None:
            return
        focused_tab.source_file = source
        focused_tab.tab_btn.setText(source.name)
