from PyQt6.QtCore import Qt
from PyQt6.QtGui import QStandardItemModel
from PyQt6.QtWidgets import QListView
from .window import LatexCompilationError
from .flashcard_model import FlashcardModel, FlashcardNotFoundException
import sys
from ..course.parse_tex import Flashcard
import logging
from ..course.courses import Courses
import threading
from ..global_utils import SectionNames, SectionNamesDescriptor
from typing import List
logger = logging.getLogger(__name__)

class FlashcardController:
    def __init__(self, view, model: FlashcardModel, config: dict) -> None:
        self.model = model
        self.view = view
        self.courses = Courses(config)
        self.flashcards = []
        self._setBindings()
        self._populate_view()

    def _setBindings(self):
        self.view.bind_next_flashcard_button(self.show_next_flashcard)
        self.view.bind_prev_flashcard_button(self.show_prev_flashcard)
        self.view.bind_show_answer_button(lambda: self.display_card("answer", "pdf_answer_path"))
        self.view.bind_show_question_button(lambda: self.display_card("question", "pdf_question_path"))
        self.view.bind_create_flashcards_button(self.create_flashcards)
        self.view.bind_flashcard_info_button(self.show_flashcard_info)
        self.view.bind_show_proof_button(lambda: self.display_card("proof", "pdf_proof_path"))

    def _populate_view(self):
        """ Use model data to populate view """
        courses = self.courses.courses.keys()
        self.view.course_combo.addItems(courses)

    def run(self, app):
        logger.info(f"Calling {self.run}")
        self.view.show()
        self.model.compile_thread.start()
        sys.exit(app.exec())


    def handle_dynamic_data(self):
        """ Flashcards must have a question and answer, however they may have other optional fields such as a proof or note
        This methods handles behaviour associated with the optional fields
        """
        if SectionNames.PROOF.name in self.model.current_card.additional_info.keys(): #type: ignore SectionNames built from dict with PROOF
            self.view.show_proof_button.setHidden(False)
        else:
            self.view.show_proof_button.setHidden(True)

    def close(self):
        logger.info(f"Stoping {self.__class__.__name__}")
        self.model.compile_thread.stop()

    def display_card(self, text_attr: str, path_attr: str):
        card = self.model.current_card
        if not card:
            self.view.set_error_message("No flashcard has been loaded... TODO write a better message")
            return

        text_attr_ = getattr(card, text_attr, None)
        path_attr_ =  getattr(card, path_attr, None)
        if text_attr_ is None or path_attr_ is None:
            raise ValueError(f"Flashcard does not have attr: {text_attr} or {path_attr}")
        try:
            self.view.plot_tex(path_attr_, text_attr_)
        except LatexCompilationError as e:
            logging.warning(f"Failed to compile card: {self.model.current_card} with tex: {text_attr_}, {e}")
            self.view.set_error_message(f"Failed to compile flashcard question. Raw latex: {text_attr_}")

    def show_next_flashcard(self):
        logger.debug(f"Calling {self.show_next_flashcard}")
        try:
            self.model.next_flashcard()
            self.handle_dynamic_data()
            self.view.flashcard_type_label.setText(f"Section name: {self.model.current_card.section_name}")
            # create some general method for handling additional info
        except FlashcardNotFoundException as e: # Implment logging and gui message properties
            logger.error(f"Failed to show next flashcard question, {e}")
            self.view.set_error_message(str(e))
        except LatexCompilationError as e:
            logger.error(f"Failed to compile next flashcard question, {e}")
            self.view.set_error_message(str(e))
        self.display_card("question", "pdf_question_path")


    def show_prev_flashcard(self):
        logger.debug(f"Calling {self.show_prev_flashcard}")
        try:
            self.model.prev_flashcard()
            self.handle_dynamic_data()
        except FlashcardNotFoundException as e:
            logger.error(f"Failed to show next flashcard question, {e}")
            self.view.set_error_message(str(e))
        except LatexCompilationError as e:
            logger.error(f"Failed to compile prev flashcard question, {e}")
            self.view.set_error_message(str(e))
        self.display_card("question", "pdf_question_path")


    def show_flashcard_info(self):
        if self.model.current_card is None:
            message = "No flashcard selected. This button display info regarding source of flashcard"
        else:
            tracked_string = self.model.current_card.question if self.view.document == self.model.current_card.pdf_question_path else self.model.current_card.answer
            source = tracked_string.source_history.root
            if len(tracked_string) >= 300:
                tracked_string = tracked_string[:301]
            message = f"Source: {source}. Latex: {str(tracked_string)}"
        self.view.flashcard_info_button.set_message(message)

    def create_flashcards(self):
        """ TODO : Using a thread to load flashcards is essentailly pointless as we dealing with cpu bound task not IO
        If we implement multiprocessing we have to avoid lock objects as there is some issues with serializing the object...
        We an use Queue but then we have no __len__() or clear() methods... have fun"""
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

    def get_flashcard_pipeline_config(self) -> tuple[str, list[SectionNamesDescriptor], set[int]]:
        """ Retreives user config from widgets. We need to do error checking... what if no boxes are checked """
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
        section_names_pretty = [item.text().upper() for item in checked_sections]
        if "All" in section_names_pretty:
            section_names = [member for member in SectionNames]
        else:
            section_names = [member for member in SectionNames if member.name in section_names_pretty]
#            section_names = [getattr(SectionNames, section_pretty).value for section_pretty in section_names_pretty if hasattr(SectionNames, section_pretty)]
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

