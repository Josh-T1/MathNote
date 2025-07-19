# #2E2E2E is a dark grey
# #d3d3d3 is a light grey
# #444 and #555 are very light grey's. #555 is lighter

TOGGLE_BUTTON_CSS = """
QPushButton {
    border-radius: 2px;
    background-color: #2E2E2E;
    width: 20px;
    height: 20px;
    font-size: 16pt;
}
"""

TREE_VIEW_CSS = """
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
"""

SVG_VIEWER_CSS = """
QSvgWidget {
        background-color: white;
        }
"""
