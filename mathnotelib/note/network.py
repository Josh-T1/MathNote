from collections.abc import Callable
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QGraphicsEllipseItem, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QListView, QMessageBox, QPinchGesture, QSizePolicy, QSpacerItem, QVBoxLayout,
                             QWidget, QPushButton, QMainWindow, QSpacerItem, QSizePolicy, QScrollArea, QApplication)
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtCore import QEvent, Qt, pyqtSignal, QPoint, QPointF
from PyQt6.QtGui import QBrush, QColor, QPainter, QPalette, QStandardItem, QStandardItemModel, QPen,QFont
import networkx as nx
import numpy as np

adj_matrix = np.array([
    [0, 1, 0, 0, 1],  # Node 0 is connected to Node 1 and Node 4
    [1, 0, 1, 1, 0],  # Node 1 is connected to Node 0, Node 2, and Node 3
    [0, 1, 0, 1, 0],  # Node 2 is connected to Node 1 and Node 3
    [0, 1, 1, 0, 1],  # Node 3 is connected to Node 1, Node 2, and Node 4
    [1, 0, 0, 1, 0],  # Node 4 is connected to Node 0 and Node 3
])


class GraphNode(QGraphicsEllipseItem):
    """
    Wrapper for QGraphicsEllipseItem that has callback option on mousePressEvent. Pass callback: Callable
    as kwarg
    """
    def __init__(self, *args, **kwargs):
        if "callback" in kwargs:
            self.callback = kwargs.pop("callback")
        super().__init__(*args, **kwargs)
#        self.callback = kwargs.get("callback", None)

    def mousePressEvent(self, event) -> None:
        if self.callback is not None:
            self.callback()
        return super().mousePressEvent(event)

class ZoomableGraphicsView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.grabGesture(Qt.GestureType.PinchGesture)
        self.scale_factor = 1.0

    def gestureEvent(self, event):
        if isinstance(event.gesture(Qt.GestureType.PinchGesture), QPinchGesture):
            pinch = event.gesture(Qt.GestureType.PinchGesture)
            if pinch.changeFlags() & QPinchGesture.ChangeFlag.ScaleFactorChanged:
                self.scale(pinch.scaleFactor(), pinch.scaleFactor())
            return True
        return False

    def event(self, event):
        if event is None:
            return
        if event.type() == QEvent.Type.Gesture:
            return self.gestureEvent(event)
        return super().event(event)

    def wheelEvent(self, event):
        if event is None:
            return
        delta = event.angleDelta().y() / 120  # Typical mouse wheel delta scaling
        factor = 1.1 if delta > 0 else 0.9
        self.scale(factor, factor)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1000, 600)
        self.setMinimumSize(400, 300)

        self.widget = QWidget()
        self.main_layout = QHBoxLayout(self.widget)
        self.main_flashcard_layout = QVBoxLayout()

        self.setCentralWidget(self.widget)
        self.initUi()


    def initUi(self):
        self._create_widgets()
        self._add_widgets()

    def _create_widgets(self):
        self.scene = QGraphicsScene()
        self.view = ZoomableGraphicsView(self.scene) # TODO
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._create_graph()

    def _add_widgets(self):
        self.main_layout.addWidget(self.view)

    def _create_graph(self):
        # Example graph
        graph = nx.Graph()
        graph.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)])

        # Generate node positions
        pos = nx.spring_layout(graph)

        # Add nodes and edges to the scene
        for node, (x, y) in pos.items():
            self._add_node(node, QPointF(x * 300, y * 300))  # Scale positions for better spacing

        for edge in graph.edges:
            self._add_edge(edge, pos)

    def _add_node(self, node, pos):
        # Add a circle for the node
        radius = 20
        node = GraphNode(pos.x() - radius, pos.y() - radius, radius * 2, radius * 2, callback=self._node_clicked)
        node.setPen(QPen(Qt.GlobalColor.black))
        node.setBrush(QBrush(Qt.GlobalColor.lightGray))
        self.scene.addItem(node)
#        ellipse.setToolTip(f"Node {node}")

        # Add a label for the node
        text = self.scene.addText(str(node), QFont("Arial", 12))
        text.setPos(pos.x() - 10, pos.y() - 10)  # Adjust for centering

        # Attach an event to the node
        node.setFlag(node.GraphicsItemFlag.ItemIsSelectable, True)
        node.setCursor(Qt.CursorShape.PointingHandCursor)


    def _add_edge(self, edge, pos):
        # Add a line for the edge
        start, end = edge
        start_pos = QPointF(pos[start][0] * 300, pos[start][1] * 300)
        end_pos = QPointF(pos[end][0] * 300, pos[end][1] * 300)
        self.scene.addLine(start_pos.x(), start_pos.y(), end_pos.x(), end_pos.y(), QPen(Qt.GlobalColor.black))

    def _node_clicked(self, node):
        # Open a PDF or perform another action
        print(f"Node {node} clicked!")
#        pdf_path = f"file:///path/to/pdf_for_node_{node}.pdf"  # Replace with actual paths
#        webbrowser.open(pdf_path)

