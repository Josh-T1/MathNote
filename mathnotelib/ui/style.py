# #2E2E2E is a dark grey
# #d3d3d3 is a light grey
# #/444 is light grey and #/555 is a very ligh grey's
# Base
COLOR_BACKGROUND        = "#2e3338"  # main viewer background
COLOR_BACKGROUND_ALT   = "#2a2e33"  # inactive tab background

# Focus states
COLOR_FOCUSED           = "#3a4046"  # focused widget background (lighter than base, subtle lift)
COLOR_FOCUSED_BORDER    = "#4a5158"  # border/outline for focused elements

# List/combo widgets
COLOR_LISTVIEW_BG       = "#26292d"  # list/combo dropdown background — darker, recedes behind content
COLOR_LISTVIEW_HOVER    = "#343a40"  # row hover state
COLOR_LISTVIEW_SELECTED = "#454c53"  # selected row — distinguishable from hover, not too bright

# Text
COLOR_TEXT_PRIMARY      = "#e8e8e8"  # main text — off-white, avoids harsh pure #fff
COLOR_TEXT_SECONDARY    = "#9a9fa5"  # dimmed text (labels, metadata, placeholders)
COLOR_TEXT_DISABLED     = "#5f6469"  # disabled/inactive text

COLOR_TAB_UNFOCUSED    = "#262a2e"  # secondary/recessed panels (darker than base)


COLOR_TAB_FOCUSED       = "#3a4046"  # active tab background (same as COLOR_FOCUSED)

TREE_VIEW_CSS = F"""
QTreeView {{
    background-color: {COLOR_LISTVIEW_BG};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid #444;
    border-radius: 4px;
    }}
QTreeView::item:selected {{
    background-color: {COLOR_LISTVIEW_SELECTED};
    color: white;
    }}
QTreeView::item:hover {{
    background-color: {COLOR_LISTVIEW_HOVER};
    color: {COLOR_TEXT_PRIMARY};
}}
"""

SVG_VIEWER_CSS = """
QSvgWidget {
        background-color: white;
        }
"""

MAIN_WINDOW_CSS = f"""
QMainWindow {{
        background-color: {COLOR_BACKGROUND};
        }}
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

LABEL_CSS = f"""
QLabel {{
    color: {COLOR_TEXT_PRIMARY};
}}
"""

BOXED_LABEL_CSS = f"""
QLabel {{
    border: 1px solid {COLOR_TEXT_SECONDARY};
    border-radius: 3px;
    background-color: {COLOR_FOCUSED};
    color: {COLOR_TEXT_PRIMARY};
    padding: 1px 18px 1px 3px;
    min-width: 6em;
}}
"""

TITLE_LABEL_CSS = f"""
QLabel {{
    font-size: 18px;
    color: {COLOR_TEXT_PRIMARY};
}}
"""

SEARCH_CSS = """
QLineEdit {
    margin: 4px;
    border-radius: 4px;
}
"""


BUTTON_CSS = f"""
QPushButton {{
    background-color: {COLOR_FOCUSED};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_FOCUSED_BORDER};
    border-radius: 6px;
    padding: 6px 12px;
}}
QPushButton:hover {{
    background-color: {COLOR_FOCUSED_BORDER};
}}
QPushButton:pressed {{
    background-color: {COLOR_BACKGROUND_ALT};
}}
QPushButton:disabled {{
    background-color: {COLOR_BACKGROUND};
    color: {COLOR_TEXT_DISABLED};
    border: 1px solid {COLOR_BACKGROUND};
}}
"""




COMBO_BOX_CSS = f"""
QComboBox {{
    border: 1px solid {COLOR_TEXT_SECONDARY};
    border-radius: 3px;
    background-color: {COLOR_FOCUSED};
    color: {COLOR_TEXT_PRIMARY};
    padding: 1px 18px 1px 3px;
    min-width: 6em;

}}
QComboBox:hover {{
    border: 1px solid {COLOR_TEXT_PRIMARY};
}}

QComboBox:focus {{
    border: 1px solid {COLOR_TEXT_PRIMARY};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border: none;
    background-color: transparent;
}}

QComboBox::down-arrow {{
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {COLOR_TEXT_SECONDARY};
    margin-right: 6px;
}}


QComboBox QAbstractItemView {{
    background-color: {COLOR_LISTVIEW_BG};
    color: {COLOR_TEXT_PRIMARY};
    outline: none;
    border: 1px solid {COLOR_FOCUSED_BORDER};
    border-radius: 4px;
}}
"""


LIST_VIEW = f"""
QListView {{
    background-color: {COLOR_LISTVIEW_BG};
    border-radius: 6px;
}}

QListView::item:selected {{
    background-color: {COLOR_LISTVIEW_BG};

}}
QListView::item {{
    padding: 4px;
}}

QListView::item:hover {{
    background-color: {COLOR_LISTVIEW_HOVER};
}}
"""
