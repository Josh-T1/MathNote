import logging

from PyQt6.QtCore import QModelIndex, QObject, Qt
from PyQt6.QtGui import QStandardItem
from PyQt6.QtWidgets import QMainWindow

from .ui_utils import with_error_dialog
from ..navbar import SettingsNavbar
from ..constants import SECTION_ROLE, LABEL_ROLE, PARENTS_ROLE
from ..dialog import NewSectionDialog, ParentSelectDialog, confirm_delete
from ...config import CONFIG, Section
from ...enums import FileType



logger = logging.getLogger(__name__)


class SettingsController(QObject):
    def __init__(self, window: QMainWindow, settings_navbar: SettingsNavbar):
        super().__init__()
        self.settings_nav = settings_navbar
        self.window = window
        self._populate_view()
        self.connect_handlers()

    def connect_handlers(self):
        self.settings_nav.new_section.connect(lambda: self.handle_new_section())
        self.settings_nav.delete_section.connect(lambda: self.handle_delete_section())
        self.settings_nav.pattern_changed.connect(lambda: self.pattern_changed())
        self.settings_nav.save_btn.clicked.connect(lambda: self.handle_save())
        self.settings_nav.section_view.doubleClicked.connect(self._on_item_double_clicked)
        self.settings_nav.experimental_export.connect(lambda checked: self.handle_export_checked(checked))
        self.settings_nav.log_level_combo.currentIndexChanged.connect(lambda level: self.handle_update_log_level(level))

    def handle_update_log_level(self, level: str):
        CONFIG.set_log_level(self.settings_nav.log_level_combo.currentText())

    def handle_export_checked(self, checked: bool):
        CONFIG.enable_exp_export = checked

    @with_error_dialog
    def handle_save(self):
        CONFIG.save()

    @with_error_dialog
    def handle_new_section(self):
        dialog = NewSectionDialog()
        if not dialog.exec():
            return
        name, typ_ptrn, tex_ptrn = dialog.get_data()
        if not typ_ptrn or not tex_ptrn:
            raise ValueError("File pattern for both Typst and LaTeX files")
        if not name:
            raise ValueError("Null section name provided. Section name must be specified")
        new_section = Section(name,{FileType.LaTeX: tex_ptrn, FileType.Typst: typ_ptrn})
        CONFIG.section_names[name] = new_section
        self._build_section(name, new_section)

    @with_error_dialog
    def handle_delete_section(self):
        idx = self.settings_nav.section_view.currentIndex()
        if not idx.isValid():
            return None
        item = self.settings_nav.section_model.itemFromIndex(idx)
        if item is None:
            return
        if item.parent() is not None:
            return None
        section_name = item.data(SECTION_ROLE)
        dependents = [
            name for name, section in CONFIG.section_names.items()
            if section_name in section.parents
        ]
        if dependents:
            raise ValueError(
                f"Cannot delete '{section_name}': it is a required parent for {', '.join(dependents)}"
            )

        confirmed = confirm_delete(self.window, section_name)
        if not confirmed:
            return

        idx = item.index()
        self.settings_nav.section_model.removeRow(idx.row(), idx.parent())
        del CONFIG.section_names[section_name]
        return

    @with_error_dialog
    def pattern_changed(self):
        return

    def _build_section(self, name: str, ftype_map):
        section_item = self._build_section_row(name, ftype_map)
        self.settings_nav.section_model.appendRow(section_item)
        index = self.settings_nav.section_model.indexFromItem(section_item)
        self.settings_nav.section_view.setFirstColumnSpanned(
            index.row(), index.parent(), True
        )

    def _populate_view(self):
        self.settings_nav.root_val.set_path(str(CONFIG.root_path))
        self.settings_nav.config_dir_val.set_path(str(CONFIG.config_dir()))
        self.settings_nav.typst_preamble_path_val.set_path(str(CONFIG.typst_preamble_path))
        self.settings_nav.latex_preamble_path_val.set_path(str(CONFIG.latex_preamble_path))
        self.settings_nav.typst_macro_path_val.set_path(str(CONFIG.typst_macro_path))
        self.settings_nav.latex_macro_path_val.set_path(str(CONFIG.latex_macro_path))
        self.settings_nav.export_checkbox.setChecked(CONFIG.enable_exp_export)

        for name, ftype_map in CONFIG.section_names.items():
            self._build_section(name, ftype_map)

    def _build_parent_row(self, section_name: str, parents: frozenset[str]):
        label_item = QStandardItem("Parents")
        label_flags = label_item.flags()
        label_flags &= ~Qt.ItemFlag.ItemIsEditable
        label_item.setFlags(label_flags)

        display_text = ", ".join(sorted(parents)) if parents else "(none)"
        value_item = QStandardItem(display_text)
        value_flags = value_item.flags()
        value_flags |= Qt.ItemFlag.ItemIsEditable
        value_item.setFlags(value_flags)
        value_item.setData(section_name, SECTION_ROLE)
        value_item.setData("parents", LABEL_ROLE)
        value_item.setData(parents, PARENTS_ROLE)
        return [label_item, value_item]

    def _build_section_row(self, section_name: str, section: Section) -> QStandardItem:
        name_item = QStandardItem(section_name)
        flags = name_item.flags()
        flags &= ~Qt.ItemFlag.ItemIsEditable
        name_item.setFlags(flags)
        name_item.setData(section_name, SECTION_ROLE)
        name_item.appendRow(self._build_pattern_row("LaTeX", section_name, section.patterns[FileType.LaTeX]))
        name_item.appendRow(self._build_pattern_row("Typst", section_name, section.patterns[FileType.Typst]))
        name_item.appendRow(self._build_parent_row(section_name, section.parents))
        return name_item

    def _build_pattern_row(self, label: str, section, value: str) -> list[QStandardItem]:
        label_item = QStandardItem(label)
        label_flags = label_item.flags()
        label_flags &= ~Qt.ItemFlag.ItemIsEditable
        label_item.setFlags(label_flags)

        value_item = QStandardItem(value)
        value_flags = value_item.flags()
        value_flags |= Qt.ItemFlag.ItemIsEditable
        value_item.setFlags(value_flags)
        value_item.setData(section, SECTION_ROLE)
        value_item.setData(label, LABEL_ROLE)
        return [label_item, value_item]


    def _on_item_double_clicked(self, index: QModelIndex):
        item = self.settings_nav.section_model.itemFromIndex(index)
        if item is None or item.data(LABEL_ROLE) != "parents":
            return  # not a parents row — let normal inline editing happen for pattern rows

        section_name = item.data(SECTION_ROLE)
        current_parents = item.data(PARENTS_ROLE)
        all_names = list(CONFIG.section_names.keys())

        dialog = ParentSelectDialog(all_names, section_name, current_parents)
        if not dialog.exec():
            return

        new_parents = dialog.get_selected()
        item.setData(new_parents, PARENTS_ROLE)
        item.setText(", ".join(sorted(new_parents)) if new_parents else "(none)")

        # persist to CONFIG immediately, or batch until save_btn — your call
        old_section = CONFIG.section_names[section_name]
        CONFIG.section_names[section_name] = Section(
            name=section_name, patterns=old_section.patterns, parents=new_parents
        )
