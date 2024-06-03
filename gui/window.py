from PyQt5.QtWidgets import QApplication, QHBoxLayout, QSizePolicy, QSpacerItem, QTextEdit, QVBoxLayout, QWidget, QPushButton, QCompleter, QMainWindow, QMenu, QAction, QSpacerItem, QSizePolicy, QLabel
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QTextDocument
import sys
import matplotlib
import matplotlib.pyplot as plt
from pathlib import Path
from .flashcard_model import FlashcardModel
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

#class LatexViewer(FigureCanvas):
#    def __init__(self, parent = None):
#        self.fig, self.ax = plt.subplots()
#        super(LatexViewer, self).__init__(self.fig)
#        self.ax.axis("off")
#        matplotlib.rcParams['text.usetex'] = True
#        matplotlib.rcParams['font.family'] = 'serif'
#
#    def plot_latex(self, latex_string):
#        print(latex_string)
#        self.ax.clear()
#        self.ax.text(0.5, 0.5, latex_string, horizontalalignment='center', verticalalignment='center', wrap=True, fontsize=20)
#        self.ax.axis('off')
#        self.draw()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUi()

    def _create_buttons(self):
        self.next_flashcard_button = QPushButton("Next", self)
        self.next_flashcard_button.setFixedSize(100, 50)

        self.prev_flashcard_button = QPushButton("Prev", self)
        self.prev_flashcard_button.setFixedSize(100, 50)

        self.show_answer_button = QPushButton("Show Answer", self)
        self.show_quesetion_button = QPushButton("Show Question", self)

    def initUi(self):
        self.resize(800, 600)
        self.setMinimumSize(400, 300)
        # create central widget and set a layout
        widget = QWidget()
        self.setCentralWidget(widget)
        main_layout = QVBoxLayout(widget)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)

        spacer = QSpacerItem(40, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        main_layout.addItem(spacer)
        button_layout = QHBoxLayout()

        self._create_buttons()

        button_layout.addStretch()
        button_layout.addWidget(self.prev_flashcard_button)
        button_layout.addWidget(self.next_flashcard_button)
        button_layout.addStretch()

        main_layout.addWidget(self.text_edit)
#        self.canvas = LatexViewer(self)

#        main_layout.addWidget(self.canvas)
        main_layout.addLayout(button_layout)


    def plot_tex(self, tex):
        pass
#        self.canvas.plot_latex(tex)

    def bind_next_flashcard_button(self, callback):
        self.next_flashcard_button.clicked.connect(callback)

    def bind_prev_flashcard_button(self, callback):
        self.prev_flashcard_button.clicked.connect(callback)

    def bind_show_answer_button(self, callback):
        self.show_answer_button.clicked.connect(callback)

    def bind_show_question_button(self, callback):
        self.show_quesetion_button.clicked.connect(callback)


#    def contextMenuEvent(self, event):
#        context = QMenu(self)
#        context.addAction(QAction("Test1", self))
#        context.addAction(QAction("Test1", self))
#        context.exec(event.globalPos())
