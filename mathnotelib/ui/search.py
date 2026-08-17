from PyQt6.QtGui import QKeyEvent, QMouseEvent
from rapidfuzz import fuzz

from PyQt6.QtWidgets import (QLineEdit, QListWidget, QVBoxLayout, QWidget)
from PyQt6.QtCore import QByteArray, QEvent, QObject, QPoint, QProcess, Qt

from .style import SEARCH_CSS


class Container(QWidget):
    def __init__(self, files):
        super().__init__()
        self.files = files
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.search_widget = SearchWidget(files=self.files)
        layout.addWidget(self.search_widget)

        self.setLayout(layout)



class SearchWidget(QWidget):
    def __init__(self, files: list[str] | None=None, buf_size: int = 50):
        super().__init__()
        self.proc = None
        self.buffer = []
        self.files = files if files is not None else []
        self.initUI()

    def set_files(self, files: list[str]):
        self.files = files

    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        self.input = QLineEdit()
        self.results = QListWidget()

        self.results.setWindowFlag(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.results.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.input.installEventFilter(self)
        self.input.setPlaceholderText("Search...")
        self.input.setClearButtonEnabled(True)
        self.input.setStyleSheet(SEARCH_CSS)
        self.input.setFixedHeight(30)
        self.results.setFixedWidth(300)
        self.results.setMaximumHeight(200)
        layout.addWidget(self.input)
        self.setLayout(layout)

        self.input.textChanged.connect(lambda text: self.run_search(text))

    def run_search(self, text: str):
        if self.proc is not None:
            self.proc.kill()
            self.proc = None

        if not text.strip() or len(self.files) == 0:
            self.results.clear()
            return

        self.proc = QProcess(self)
        pattern = text.strip() if text.strip() else "."
        args = ["--line-number", "--no-heading", pattern] + self.files
        self.proc.readyReadStandardOutput.connect(lambda: self.handle_stdout())
        self.proc.finished.connect(lambda: self.handle_stdout())
        self.proc.start("rg", args)

        pos = self.input.mapToGlobal(QPoint(0, self.input.height()))
        self.results.move(pos)
        self.results.show()

    def handle_stdout(self):
        if self.proc is None:
            return
        data: QByteArray = self.proc.readAllStandardOutput()
        text = data.data().decode("utf-8")
        query = self.input.text().strip()
        for line in text.splitlines():
            file_path, line_num, text = line.split(":", 2)
            score = fuzz.WRatio(query, text)
            self.buffer.append((score, query, file_path, line_num, text))
        self.buffer.sort(key=lambda x: x[0], reverse=True)
        self.buffer = [b for b in self.buffer if b[1] == query]
        self.buffer = self.buffer[:50]
        self.results.clear()
        for (score, query, n, text) in self.buffer:
            self.results.addItem(f"{n}:{text}")


class EventFilter(QObject):
    def __init__(self, search_widget: SearchWidget):
        super().__init__()
        self.search_widget = search_widget
        self.search_results = self.search_widget.results
        self.search_input = self.search_widget.input

    def eventFilter(self, a0: QObject | None, a1: QEvent | None) -> bool:
        if a0 is None or a1 is None:
            return super().eventFilter(a0, a1)
        if isinstance(a1, QMouseEvent) and a1.type() == QEvent.Type.MouseButtonPress:
            global_pos = a1.globalPosition().toPoint()
            if not self.search_input.geometry().contains(self.search_input.mapFromGlobal(global_pos)):
                self.search_results.hide()
                self.search_input.clear()
                self.search_input.clearFocus()

        if a0 is self.search_input and a1.type() == QEvent.Type.FocusOut:
            self.search_results.hide()

        if a1.type() == QEvent.Type.KeyPress and isinstance(a1, QKeyEvent):
            if a1.key() == Qt.Key.Key_Escape:
                self.search_results.hide()
                self.search_input.clear()
                self.search_input.clearFocus()

        return super().eventFilter(a0, a1)
