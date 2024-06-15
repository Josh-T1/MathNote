from PyQt6.QtCore import QAbstractItemModel, Qt
from PyQt6.QtGui import QStandardItemModel
from PyQt6.QtWidgets import QListView
from .window import LatexCompilationError
from .flashcard_model import FlashcardNotFoundException, FlashcardModel, TexCompilationManager
from ..course.parse_tex import FlashcardsPipeline
import sys
import logging
from ..course.courses import Courses
from ..global_utils import get_config

logger = logging.getLogger(__name__)

class FlashcardController:
    def __init__(self, view, model, config) -> None:
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
        logger.info("Running FlashcardController")
        self.view.show()
        self.model.compile_thread.start()
        sys.exit(app.exec())

    def show_next_flashcard(self):
        logger.debug(f"Calling {self.show_next_flashcard}")
        try:
            self.model.next_flashcard()
            self.show_question()
        except FlashcardNotFoundException as e: # Implment logging and gui message properties
            logger.error(f"Failed to show next flashcard question, {e}")
            self.view.set_error_message(str(e))
        except LatexCompilationError as e:
            logger.error(f"Failed to compile next flashcard question, {e}")
            self.view.set_error_message(str(e))

    def close(self):
        logger.info("Closing FlashcardController")
        self.model.compile_thread.stop()

    def show_prev_flashcard(self):
        logger.debug(f"Calling {self.show_prev_flashcard}")
        try:
            self.model.prev_flashcard()
            self.show_question()
        except FlashcardNotFoundException as e:
            logger.error(f"Failed to show next flashcard question, {e}")
            self.view.set_error_message(str(e))
        except LatexCompilationError as e:
            logger.error(f"Failed to compile prev flashcard question, {e}")
            self.view.set_error_message(str(e))

    def show_question(self):
        if not self.model.current_card:
            self.view.set_error_message("No flashcard has been loaded... TODO write a better message")
            return
        try:
            self.view.plot_tex(self.model.current_card.pdf_question_path)
        except LatexCompilationError as e:
            logging.warning(f"Failed to compile card: {self.model.current_card} with tex: {self.model.current_card.question}, {e}")
            self.view.set_error_message(f"Failed to compile flashcard question, raw latex: {self.model.current_card.question}")

    def show_answer(self):
        if not self.model.current_card:
            self.view.set_error_message("No flashcard has been loaded... TODO write a better message")
            return
        try:
            self.view.plot_tex(self.model.current_card.pdf_answer_path)
        except LatexCompilationError as e:
            logging.warning(f"Failed to compile card: {self.model.current_card} with tex: {self.model.current_card.answer}, {e}")
            self.view.set_error_message(f"Failed to compile flashcard answer, raw latex: {self.model.current_card.answer}")


    def create_flashcards(self):
        course_name, section_names = self.get_flashcard_pipeline_config()
        course = self.courses.get_course(course_name)

        if not course:
            logger.error(f"Course: {course} is not a recognized course")
            self.view.set_error_message(f"There appears to be an issue '{course}' is not recognized")
            return

        paths = [lecture.path for lecture in course.lectures]
        self.model.load_flashcards(section_names, paths[:4]) # TDOO: fix this at some point



    def get_flashcard_pipeline_config(self):
        """ Retreives user config from widgets. We need to do error checking... what if no boxes are checked """
        pretty_section_name_to_section_name = {
                "definition": "defin", "theorem": "theo", "derivation": "der"
                }
        course_name = self.view.course_combo.currentText()
        checked_sections = self._get_checked_items_from_listView(self.view.section_list)
        section_names_pretty = [item.text() for item in checked_sections]

        if "all" in section_names_pretty:
            section_names = [name for name in pretty_section_name_to_section_name.values()]
        else:
            section_names = [pretty_section_name_to_section_name[section_name] for section_name in section_names_pretty]
        logger.debug(f"Pipeline config, course name: {course_name}, section_names: {section_names}")
        return course_name, section_names

    def _get_checked_items_from_listView(self, listview: QListView):
        """ Given a QListView object, all items that are in the 'checked' state are returned """
        checked_items = []
        model: QStandardItemModel | None = listview.model() #type: ignore
        if model:
            for i in range(model.rowCount()):
                item = model.item(i)
                if item and item.checkState() == Qt.CheckState.Checked: #type: ignore
                    checked_items.append(item)
        return checked_items

