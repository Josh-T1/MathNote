PIPELINE_FILENAME = "/Users/joshuataylor/documents/python/myprojects/mathnote/shortcut_manager/pipeline.txt"
LOCK_FILENAME = "/Users/joshuataylor/documents/python/myprojects/mathnote/shortcut_manager/lock.txt.lock"

def include_fig(name: str) -> str:
    """ returns latex code to include figure, where figure is assumed to live in figures folder (/class/figures) """
    return fr"""
\begin{{figure}}[ht]
    \centering
    \incfig{{{name}}}
    \label{{{name}}}
\end{{figure}}
"""

def latex_document(latex: str) -> str: # could i add path to macros and preamble, does this slow down the process?
    """ return latex template for embeding latex into inkscape """
    return r"""
\documentclass[12pt,border=12pt]{standalone}
\usepackage{amsmath, amssymb}
\newcommand{\R}{\mathbb R}
\begin{document}
    """ + latex + r"""
\end{document}"""

