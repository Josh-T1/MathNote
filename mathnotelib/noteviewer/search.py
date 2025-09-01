import subprocess
from PyQt6.QtGui import QMouseEvent
from rapidfuzz import fuzz

from PyQt6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame, QGestureEvent, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow, QMenu, QPinchGesture, QPushButton, QRadioButton, QScrollArea, QSizePolicy,
                             QSpacerItem, QStackedWidget, QStyle, QStyleOptionViewItem, QToolBar, QTreeView, QVBoxLayout, QWidget)
from PyQt6.QtCore import QByteArray, QEvent, QFileSystemWatcher, QLine, QModelIndex, QObject, QPoint, QProcess, QSize, QTimer, pyqtSignal, Qt

from .style import SEARCH_CSS
from ..repo import NotesRepository
from ..utils import CONFIG


def main():
    notes_dir = "/Users/joshuataylor/MathNote/Notes"
    cmd = f"rg --line-number --no-heading '' {notes_dir} | fzf"

    rg = subprocess.Popen(["rg", "--line-number", "--no-heading", "", notes_dir], stdout=subprocess.PIPE)
    fzf = subprocess.Popen(["fzf"], stdin=rg.stdout)
    if rg.stdout:
        print("stdout")
        rg.stdout.close()
    out, _ = fzf.communicate()
    return out


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


def get_files():
    cf = CONFIG
    notes_manager = NotesRepository(cf.root_path / "Notes")
    notes = notes_manager.root_category.notes
    return [str(note.path) for note in notes]

def test(files):
    buffer = []
    patterns = ["d", "de", "def"]
    with open("/Users/joshuataylor/out.txt", "a") as f:
        for p in patterns:
            f.write(f"============ {p} ===========\n")
            args = ["rg", "--line-number", "--no-heading", p] + files
            res = subprocess.run(args, capture_output=True)
            if res.stdout is not None:
                stream = res.stdout
                text = stream.decode("utf-8")
                for l in text.splitlines():
                    file_path, line_num, text = l.split(":", 2)
                    score = fuzz.WRatio(p, text)
                    buffer.append((score, line_num, text))
            buffer.sort(key=lambda x: x[0], reverse=True)

            for i in range(min(len(buffer), 50)):
                f.write(str(buffer[i]) + "\n")
            buffer.clear()

if __name__ == "__main__":
    import sys
    files = [
            "/Users/joshuataylor/MathNote/Courses/math-617/main/lectures/lec_03.tex",
            "/Users/joshuataylor/MathNote/Courses/math-617/main/lectures/lec_04.tex"
            ]
#    test(files)
    app = QApplication(sys.argv)
    w = Container(files)
#    w = MSearchWidget(files)
    w.show()
    sys.exit(app.exec())

