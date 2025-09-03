from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout,
                             QHBoxLayout, QLineEdit, QMessageBox ,QTimeEdit,QWidget)

from .._enums import FileType


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


class NewNoteDialog(QDialog):
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
