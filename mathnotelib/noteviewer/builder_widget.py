from PyQt6.QtWidgets import (QApplication, QButtonGroup, QFrame, QGestureEvent, QGraphicsRectItem, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QListWidget, QMainWindow, QPinchGesture, QPushButton, QScrollArea, QSizePolicy,
                             QSpacerItem, QStyle, QStyleOptionViewItem, QToolBar, QTreeView, QVBoxLayout, QWidget)
from PyQt6.QtCore import QEvent, QFileSystemWatcher, QModelIndex, QProcess, QTimer, pyqtSignal, Qt
from PyQt6.QtSvgWidgets import QGraphicsSvgItem, QSvgWidget

from .style import BUILDER_LIST_CSS


class DocumentBuilder(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.main_layout)
        self.initUI()

    def initUI(self):
        self._create_widgets()
        self._configure_widgets()
        self._add_widgets()

    def _create_widgets(self):
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(BUILDER_LIST_CSS)

    def _add_widgets(self):
        self.main_layout.addWidget(self.list_widget)

    def _configure_widgets(self):
        self.list_widget.setDragEnabled(True)
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
