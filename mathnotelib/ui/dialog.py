from PyQt6.QtCore import QLine, Qt
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
                             QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton ,QTimeEdit, QVBoxLayout,QWidget)

from ..enums import FileType



def show_error_dialog(window: QWidget, msg: str):
    dialog = QMessageBox(window)
    dialog.setIcon(QMessageBox.Icon.Critical)
    dialog.setWindowTitle("Error")
    dialog.setText(msg)
    dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
    dialog.exec()

class NewCourseDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QFormLayout()
        self.setLayout(layout)
        self.name = QLineEdit()

        self.ftype_combo = QComboBox()
        self.weekday_selector = DaysOfWeekSelector()
        self.start_time_edit = QTimeEdit()
        self.end_time_edit = QTimeEdit()
        self.start_date = QDateEdit()
        self.end_date = QDateEdit()
        self.ftype_combo.addItems(["Typst", "LaTeX"])
        self.end_time_edit.setDisplayFormat("HH:mm")
        self.start_time_edit.setDisplayFormat("HH:mm")
        self.start_date.setDisplayFormat("yyyy/MM/dd")
        self.end_date.setDisplayFormat("yyyy/MM/dd")
        layout.addRow("Name:", self.name)
        layout.addRow("File Type:", self.ftype_combo)
        layout.addRow("Weekdays:", self.weekday_selector)
        layout.addRow("Start Time:", self.start_time_edit)
        layout.addRow("End Time:", self.end_time_edit)
        layout.addRow("Start Date:", self.start_date)
        layout.addRow("End Date:", self.end_date)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self) -> tuple[str, FileType, str, str, list[str], str, str]:
        name = self.name.text()
        ftype = FileType.LaTeX if self.ftype_combo.currentText() == "LaTeX" else FileType.Typst
        start_time = self.start_time_edit.time().toString("HH:mm")
        end_time = self.end_time_edit.time().toString("HH:mm")
        weekdays = self.weekday_selector.get_selected_days()
        start_date = self.start_date.date().toString("yyyy/MM/dd")
        end_date = self.end_date.date().toString("yyyy/MM/dd")
        return name, ftype, start_time, end_time, weekdays, start_date, end_date

class NameDialog(QDialog):
    def __init__(self, title: str | None=None):
        super().__init__()
        self.title = title
        self.initUI()

    def initUI(self):
        layout = QFormLayout()
        self.setLayout(layout)
        if self.title is not None:
            self.setWindowTitle(self.title)
        self.name = QLineEdit()
        layout.addRow("Name:", self.name)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        return self.name.text()


class NewTypesetFileDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QFormLayout()
        self.setLayout(layout)
        self.name = QLineEdit()
        layout.addRow("Name:", self.name)
        self.ftype_combo = QComboBox()
        self.ftype_combo.addItems(["Typst", "LaTeX"])
        layout.addRow("File Type", self.ftype_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def get_data(self):
        ftype = FileType.LaTeX if self.ftype_combo.currentText() == "LaTeX" else FileType.Typst
        return self.name.text(), ftype


class DaysOfWeekSelector(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        self.checkboxes = {}
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for d in days:
            cb = QCheckBox(d)
            layout.addWidget(cb)
            self.checkboxes[d] = cb

    def get_selected_days(self) -> list:
        return [day for day, cb in self.checkboxes.items() if cb.isChecked()]

    def set_selected_days(self, days):
        for d, cb in self.checkboxes.items():
            cb.setChecked(d in days)

def confirm_delete(window: QWidget, item_name: str) -> bool:
    """
    Show a confirmation dialog before deleting.

    Args:
        parent: Parent widget (e.g. main window).
        name: Name of the object to delete.
        kind: Type of object (e.g. "note", "course", "file").

    Returns:
        True if user confirmed, False otherwise.
    """
    msg = QMessageBox(window)
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setWindowTitle(f"Delete {item_name}")
    msg.setText(f"Are you sure you want to delete '{item_name}'?")
    msg.setInformativeText("This action cannot be undone.")
    msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
    msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
    result = msg.exec()
    return result == QMessageBox.StandardButton.Yes


class NewSectionDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QFormLayout()
        self.name = QLineEdit()
        self.typst_pattern = QLineEdit()
        self.latex_pattern = QLineEdit()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)


        layout.addRow("Name:", self.name)
        layout.addRow("Typst pattern", self.typst_pattern)
        layout.addRow("LaTeX pattern", self.latex_pattern)


        self.setLayout(layout)
        self.setWindowTitle("New Section")

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self) -> tuple[str, str, str]:
        name = " ".join([word.lower().capitalize() for word in self.name.text().split()])
        return (name, self.typst_pattern.text(), self.latex_pattern.text())


class ParentSelectDialog(QDialog):
    def __init__(self, all_section_names: list[str], current_section: str, selected_parents: frozenset[str]):
        super().__init__()
        self.setWindowTitle(f"Select parents for {current_section}")
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        # a section can't be its own parent — exclude it
        for name in sorted(n for n in all_section_names if n != current_section):
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if name in selected_parents else Qt.CheckState.Unchecked
            )
            self.list_widget.addItem(item)

        btn_row = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def get_selected(self) -> frozenset[str]:
        result = set()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item is None:
                return frozenset()
            if item.checkState() == Qt.CheckState.Checked:
                result.add(item.text())
        return frozenset(result)
