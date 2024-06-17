from random import shuffle
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
import threading
from functools import partial

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
        self.view.bind_flashcard_info_button(self.show_flashcard_info)
        self.populate_view()

    def populate_view(self):
        """ Use model data to populate view """
        courses = self.courses.courses().keys()
        self.view.course_combo.addItems(courses)

    def run(self, app):
        logger.info(f"Calling {self.run}")
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
        logger.info(f"Stoping {self.__class__.__name__}")
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

    def show_flashcard_info(self):
        if self.model.current_card is None:
            message = "No flashcard selected. This button display info regarding source of flashcard"
        else:
            tracked_string = self.model.current_card.question if self.view.document == self.model.current_card.pdf_question_path else self.model.current_card.answer
            source = tracked_string._source_history.root_source
            if len(tracked_string) >= 300:
                tracked_string = tracked_string[:301]
            message = f"Source: {source}. Latex: {str(tracked_string)}"
        self.view.flashcard_info_button.set_message(message)

    def create_flashcards(self):
        """ TODO : Using a thread to load flashcards is essentailly pointless as we dealing with cpu bound task not IO
        Im we implement multiprocessing we have to avoind lock objects as there is some issues with serializing the object...
        We an use Queue but then we have no __len__() or clear() methods."""
        course_name, section_names, weeks = self.get_flashcard_pipeline_config()
        course = self.courses.get_course(course_name)

        # catch user errors
        if not section_names or not course:
            self.view.set_error_message(f"Invalid selection course={course}, section names={section_names}. You must select a course name and at least one section")
            logger.info(f"Invalid selection (course={course}, section_names={section_names}) for generating flashcards")
            return

        paths = [lecture.path for lecture in course.lectures if course.get_week(lecture) in weeks]
        load_thread = threading.Thread(target=self.model.load_flashcards, args=(section_names, paths))
        load_thread.start()
#        self.model.load_flashcards(section_names, paths)

    def get_flashcard_pipeline_config(self):
        """ Retreives user config from widgets. We need to do error checking... what if no boxes are checked """
        pretty_section_name_to_section_name = {
                "definition": "defin", "theorem": "theo", "derivation": "der"
                }
        course_name = self.view.course_combo.currentText()
        checked_sections = self._get_checked_items_from_listView(self.view.section_list)
        weeks_items = self._get_checked_items_from_listView(self.view.filter_by_week_list)
        weeks_text = [week.text() for week in weeks_items]
        # Clean filter by weeks params
        if "All" in weeks_text or not weeks_text:
            weeks = {i for i in range(1, 13+1)} # TODO: verify weeks
        else:
            weeks = {int(week.split(" ")[-1]) for week in weeks_text}

        # Clean checked section params
        section_names_pretty = [item.text() for item in checked_sections]
        if "All" in section_names_pretty:
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

