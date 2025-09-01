# #2E2E2E is a dark grey
# #d3d3d3 is a light grey
# #444 is light grey and #555 is a very ligh grey's

BUILDER_LIST_CSS = """
QListView {
    background-color: #2E2E2E;
    color: #d3d3d3;
    border: 1px solid #444;
    }
QListView::item:selected {
    background-color: #444;
    color: white;
    }
QListView::item:hover {
    background-color: #555;
    color: white;
}
"""

TREE_VIEW_CSS = """
QTreeView {
    background-color: #2E2E2E;
    color: #d3d3d3;
    border: 1px solid #444;
    border-radius: 4px;
    }
QTreeView::item:selected {
    background-color: #444;
    color: white;
    }
QTreeView::item:hover {
    background-color: #555;
    color: white;
}
"""

SVG_VIEWER_CSS = """
QSvgWidget {
        background-color: white;
        }
"""

MAIN_WINDOW_CSS = """
QMainWindow {
        background-color: #2E2E2E;
        }
"""

TAB_BTN_EMPTY_CSS = """
QPushButton {
    border: none;
    background: transparent;
    border-radius: 4px;
}
QPushButton:hover {
    background: transparent;
    border-radius: 4px;
}
"""

TAB_BTN_CSS = """
QPushButton {
    margin: 3px;
    border: none;
    background: transparent;
    text-align: left;
    border-radius: 4px;
}
QPushButton:hover {
    background: transparent;
    border-radius: 4px;
}
"""

CLOSE_TAB_BTN_CSS = """
QPushButton {
    border: none;
    background: transparent;
}
QPushButton:hover {
    background: rgba(0,0,0,0.1);
    border-radius: 4px;
}
"""

TAB_WIDGET_CSS = """
QWidget:hover {
    background-color: #555;
}
"""

ICON_CSS = """
QPushButton {
    border: none;
    background: transparent;
}
QPushButton:hover {
    background: #555;
    border-radius: 4px;
}
"""

PAGE_INPUT_CSS = """
QLineEdit {
    background-color: rgba(211, 211, 211, 128);
    color: #2E2E2E;
    border-radius: 4px;
    padding: 2px;
}
"""

SWITCH_CSS = """
QPushButton {
    border: 0px solid #d3d3d3;
    margin: 0px;
    padding: 0px 0px;
    border-radius: 4px;
}
QPushButton:checked {
    background-color: #555;
    color: #d3d3d3;
}
"""

LABEL_CSS = """
QLabel {
    color: #d3d3d3;
}
"""

TITLE_LABEL_CSS = """
QLabel {
    font-size: 16px;
    color: #d3d3d3;
}
"""

SEARCH_CSS = """
QLineEdit {
    margin: 4px;
    border-radius: 4px;
}
"""
