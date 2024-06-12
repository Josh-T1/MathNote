from PyQt6.QtCore import QAbstractItemModel
from PyQt6.QtGui import QStandardItemModel
from PyQt6.QtWidgets import QListView
from .window import LatexCompilationError
from .flashcard_model import FlashcardNotFoundException, FlashcardModel, TexCompilationManager
from ..course.parse_tex import FlashcardsPipeline
import sys

from ..course.courses import Courses
from ..course.utils import get_config
config = get_config()

class FlashcardController:
    def __init__(self, view, model) -> None:
        self.model = model
        self.view = view
        self.courses = Courses(config)
        self.flashcards = []
        self.view.bind_next_flashcard_button(self.show_next_flashcard)
        self.view.bind_prev_flashcard_button(self.show_prev_flashcard)
        self.view.bind_show_answer_button(self.show_answer)
        self.view.bind_show_question_button(self.show_question)
        self.view.bind_create_flashcards_button(self.create_flashcards)
        self.populate_view()

    def populate_view(self):
        """ Use model data to populate view """
        courses = self.courses.courses().keys()
        self.view.course_combo.addItems(courses)

    def run(self, app):
        self.view.show()
        self.model.compile_thread.start()
        sys.exit(app.exec())

    def show_next_flashcard(self):
        try:
            self.model.next_flashcard()
            self.show_question()
        except FlashcardNotFoundException as e: # Implment logging and gui message properties
            self.view.set_error_message(str(e))
        except LatexCompilationError as e:
            self.view.set_error_message(str(e))

    def close(self):
        self.model.compile_thread.stop()

    def show_prev_flashcard(self):
        try:
            self.model.prev_flashcard()
            self.show_question()
        except FlashcardNotFoundException as e:
            self.view.set_error_message(str(e))
        except LatexCompilationError as e:
            self.view.set_error_message(str(e))

    def show_question(self):
        if not self.model.current_card:
            return
        self.view.plot_tex(self.model.current_card)

    def show_answer(self):
        if not self.model.current_card:
            return
        self.view.plot_tex(self.model.current_card, question=False)

    def create_flashcards(self):
        course_name, section_names = self.get_flashcard_pipeline_config()
        course = self.courses.get_course(course_name)

        if not course:
            # TODO logging
            return

        paths = [lecture.path for lecture in course.lectures]
        self.model.load_flashcards(section_names, paths[3:4])



    def get_flashcard_pipeline_config(self):
        """ retreives config from widgets """
        pretty_section_name_to_section_name = {
                "definition": "defin", "theorem": "theo", "derivation": "der"
                }
        course_name = self.view.course_combo.currentText()
        section_names_pretty = self._get_checked_items_from_listView(self.view.section_list)
        if "all" in section_names_pretty:
            section_names = [name for name in pretty_section_name_to_section_name.values()]
        else:
            section_names = [pretty_section_name_to_section_name[model_item.text()] for model_item in section_names_pretty]
        return course_name, section_names

    def _get_checked_items_from_listView(self, listview: QListView):
        checked_items = []
        model: QStandardItemModel | None = listview.model() #type: ignore
        if model:
            for i in range(model.rowCount()):
                item = model.item(i)
                if item.checkState(): #type: ignore
                    checked_items.append(item.text())
        return checked_items

