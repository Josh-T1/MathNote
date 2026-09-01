from io import UnsupportedOperation
import tempfile
from pathlib import Path
import logging

from PyQt6.QtCore import QFileSystemWatcher, QTimer
from PyQt6.QtWidgets import QMainWindow

from .ui_utils import with_error_dialog
from ..constants import OUTPUT_FILE_STEM
from ..file_viewer import TabWidget, TabbedSvgViewer
from ...models import SourceFile
from ...services import CompileOptions, compile_source
from ...enums import OutputFormat


logger = logging.getLogger("mathnote")



class LiveTypstController:
    DEBOUNCE = 20

    def __init__(self, window: QMainWindow, viewer: TabbedSvgViewer):
        super().__init__()
        self.viewer = viewer
        self.viewer.tab_changed.connect(self.update_tab)
        self.window = window # Used by @with_error_dialog
        self.live_file: SourceFile | None = None
        self.live_files: list[SourceFile] = []

        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self.compile_typst)

        self.watcher = QFileSystemWatcher()
        self.watcher.fileChanged.connect(lambda path: self.on_typ_changed(path))

        self.connect_handlers()

    def update_tab(self) -> None:
        for tab in self.viewer.tab_bar.get_tabs():
            if not tab.is_focused:
                continue
            sc = tab.source_file
            if sc is None:
                return
            current_tab = self.viewer.tab_bar.get_focused_tab()
            if current_tab is None:
                return
            self.live_file = current_tab.source_file
            self.compile_typst()
            return

    @with_error_dialog
    def toggle_live_preview(self) -> bool:
        source_file: None | SourceFile = None
        is_live: bool = False

        layout = self.viewer.tab_bar.main_layout

        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is None:
                continue
            tab = item.widget()
            if not isinstance(tab, TabWidget):
                continue
            if not tab.is_focused:
                continue
            source_file = tab.source_file
            is_live = tab.is_live

        if source_file is None:
            return False

        if source_file.path.suffix != ".typ":
            raise UnsupportedOperation(f"Live preview is only supported for typst files (.typ) not '{source_file.path.suffix}'")

        if is_live:
            self.watcher.removePath(str(source_file.path))
        else:
            self.watcher.addPath(str(source_file.path))
        return True

    def connect_handlers(self):
        self.viewer.tab_bar.preview.connect(self.toggle_live_preview)
        self.viewer.tab_bar.preview.connect(self.viewer.tab_bar.toggle_live)

    def on_typ_changed(self, path: str):
        current_tab = self.viewer.tab_bar.get_focused_tab()
        if current_tab is None:
            return

        self.live_file = current_tab.source_file

        if self.live_file is None or str(self.live_file.path) != path or not current_tab.is_live:
            return

        if self._debounce_timer and not self._debounce_timer.isActive():
            self._debounce_timer.start(self.DEBOUNCE)

    @with_error_dialog
    def compile_typst(self):
        if self.live_file is None:
            return
        tmpdir = tempfile.TemporaryDirectory() # Does this get cleaned up?
        tmpdir_path = Path(tmpdir.name)

        options = CompileOptions(self.live_file.path, OutputFormat.SVG, multi_page=True)
        options.set_output_dir(tmpdir_path)
        options.set_output_file_stem(OUTPUT_FILE_STEM)

        compilation_res = compile_source(self.live_file, options)
        svg_files = sorted(tmpdir_path.glob(f"{OUTPUT_FILE_STEM}*.svg"), key=rendered_sorted_key)
        if len(svg_files) == 0: #TODO seems like live compile breaks this
            return

        self._update_svg(svg_files, tmpdir, self.live_file)

    def _update_svg(self,
                    path: Path | list[Path],
                    tmpdir: tempfile.TemporaryDirectory,
                    source: SourceFile | None=None,
                    ):
        paths = path if isinstance(path, list) else [path]
        if all(p.exists() for p in paths):
            self.viewer.load_current_viewer([str(p) for p in paths], tmpdir=tmpdir, source=source, preserve_state=True)

