import os
import sys
from PyQt6.QtGui import QBrush, QColor, QFileSystemModel, QFont, QPalette, QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QMainWindow, QPlainTextEdit, QPushButton, QSizePolicy, QSpacerItem, QTreeView, QVBoxLayout, QWidget
from PyQt6.QtCore import QFileSystemWatcher, QSize, QTimer, QUrl, QProcess, pyqtSignal
from PyQt6.QtSvgWidgets import QSvgWidget
from ..utils import config
from ..note import NotesManager, serialize_category
from pathlib import Path

ROOT_DIR = Path(config["root"])

TYP_FILE = "/tmp/live.typ"
SVG_FILE = "/tmp/live.svg"

class Navbar(QWidget):
    file_opened = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.tree_visible: bool = True

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)
        self.setFixedWidth(200)

        self.initUI()

    def initUI(self):
        self._create_widgets()
        self._add_widgets()

        self._populate_tree()

    def _create_widgets(self):
        palette = QPalette()

        self.toggle_button = QPushButton("x")
        self.menu_bar_layout = QHBoxLayout()
        self.toggle_button.setStyleSheet("""
                                         QPushButton {
                                             border-radius: 2px;
                                             background-color: #2E2E2E;
                                             width: 20px;
                                             height: 20px;
                                             font-size: 16pt;
                                             }
                                         """)
        self.toggle_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.toggle_button.clicked.connect(self.toggle_tree)
        self.model = QStandardItemModel()
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setPalette(palette)
        self.tree.setFrameShape(QFrame.Shape.NoFrame)
        self.tree.header().hide() #TODO: don't think header() every returns none..
        self.root_item = self.model.invisibleRootItem()

        self.tree.setStyleSheet("""
                       QTreeView {
                           background-color: #2E2E2E;
                           color: #d3d3d3;
                       }
                       QTreeView::item:selected {
                           background-color: #444;
                           color: white;
                       }
                       QTreeView::item:hover {
                           background-color: #555;
                           color: white;
                       }
                           """)

    def _add_widgets(self):
        self.menu_bar_layout.addWidget(self.toggle_button)
#        self.hidden_layout.setFixedWidth(40)
        self.menu_bar_layout.addSpacerItem(QSpacerItem(15, 15, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        self.main_layout.addLayout(self.menu_bar_layout)
        self.main_layout.addWidget(self.tree)

    def populate_tree(self):
        notes_dir = ROOT_DIR / "Notes"
        notes = NotesManager(notes_dir)
        notes_tree = serialize_category(notes.root_category)

        def add_items(parent: QStandardItem, data: dict):
            for cat, meta in data.items():
                dir_item = QStandardItem(cat)
                parent.appendRow(dir_item)
                for note in meta["notes"]:
                    item = QStandardItem(note["name"])
                    dir_item.appendRow(item)
                for child in meta["children"]:
                    add_items(dir_item, child)

        add_items(self.root_item, notes_tree)

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
        self.compile_typst()
        self.watcher.addPath(TYP_FILE)

    def initUi(self):
        self.setStyleSheet("QMainWindow { background-color: #2E2E2E; }")
        self._create_widgets()
        self._add_widgets()

    def _create_widgets(self):
        self.viewer = QSvgWidget()
        self.viewer.setFixedSize(800, 1000)
        self.watcher = QFileSystemWatcher()
        self.watcher.fileChanged.connect(self.on_typ_changed)

        self.nav_bar = Navbar()

    def _add_widgets(self):
        self.main_layout.addWidget(self.nav_bar)
        self.main_layout.addWidget(self.viewer)

    def on_typ_changed(self):
        self.watcher.removePath(TYP_FILE)
        self.watcher.addPath(TYP_FILE)
        self.compile_typst()

    def compile_typst(self):
        self.process = QProcess()
        self.process.finished.connect(self.update_svg)
        self.process.start("typst", ["compile", TYP_FILE, "--format", "svg"])

    def update_svg(self):
        if os.path.exists(SVG_FILE):
            self.viewer.load(SVG_FILE)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec())
