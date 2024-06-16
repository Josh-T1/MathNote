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
        logger.info(f"Running {self.__class__.__name__}")
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
        logger.info(f"Closing {self.__class__.__name__}")
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
            self.view.set_error_message(f"Failed to compile flashcard question. Raw latex: {self.model.current_card.question}")

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
        course_name, section_names, weeks = self.get_flashcard_pipeline_config()
        course = self.courses.get_course(course_name)

        # catch user errors
        if not section_names or not course:
            self.view.set_error_message(f"Invalid selection course={course}, section names={section_names}. You must select a course name and at least one section")
            logger.info(f"Invalid selection (course={course}, section_names={section_names}) for generating flashcards")
            return

        paths = [lecture.path for lecture in course.lectures if course.get_week(lecture) in weeks]
        self.model.load_flashcards(section_names, paths) # TDOO: fix this at some point
#        try:
#            self.model.next_flashcard()
#        except FlashcardNotFoundException as e:
#            logger.info("No flashcards available")
#            self.view.set_error_message("No flashcards available for your given selection")


    def get_flashcard_pipeline_config(self):
        """ Retreives user config from widgets. We need to do error checking... what if no boxes are checked """
        pretty_section_name_to_section_name = {
                "definition": "defin", "theorem": "theo", "derivation": "der"
                }
        course_name = self.view.course_combo.currentText()
        checked_sections = self._get_checked_items_from_listView(self.view.section_list)
        weeks = self._get_checked_items_from_listView(self.view.filter_by_week_list)
        # Clean filter by weeks params
        if "All" in weeks or not weeks:
            weeks = {i for i in range(1, 13+1)} # TODO: verify weeks
        else:
            weeks = {int(week.text().split(" ")[-1]) for week in weeks}

        # Clean checked section params
        section_names_pretty = [item.text() for item in checked_sections]
        if "all" in section_names_pretty:
            section_names = [name for name in pretty_section_name_to_section_name.values()]
        else:
            section_names = [pretty_section_name_to_section_name[section_name] for section_name in section_names_pretty]
        return course_name, section_names, weeks

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

