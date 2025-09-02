import math
from pathlib import Path
import sys
import logging
import threading

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QApplication, QListView

from mathnotelib.models.courses import Course

from .window import FlashcardMainWindow
from .flashcard_model import FlashcardModel
from ..exceptions import FlashcardNotFoundException, LaTeXCompilationError
from ..services import CourseRepository, open_file_with_editor, open_pdf
from ..models import SectionNames, SectionNamesDescriptor
from ..config import Config

logger = logging.getLogger("mathnote")


class FlashcardController:
    def __init__(self, view: FlashcardMainWindow, model: FlashcardModel, config: Config) -> None:
        self.model = model
        self.view = view
        self.course_repo = CourseRepository(config)
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
        self.view.bind_show_proof_button(lambda: self.display_card("PROOF", "pdf_PROOF_path"))
        self.view.bind_open_main_button(self.open_main)
        self.view.bind_launch_iterm_button(self.launch_iterm)
        self.view.config_bar.update_filters.connect(lambda: self.handle_update_filters())

    def handle_update_filters(self):
        text = self.view.course_combo().currentText()
        course: Course | None = self.course_repo.get_course(text)
        if course is None:
            raise ValueError("Course directory not found")
        day_per_week = max(len(course.days()), 2) # defualt to 2 if not set in course_info.json
        num_weeks = math.ceil(len(course.lectures) / day_per_week)

        self.view.list_model().clear()
        all_box = QStandardItem('All')
        all_box.setCheckable(True)
        self.view.list_model().appendRow(all_box)
        for i in range(1, num_weeks+1):
            list_item = QStandardItem(f"Week {i}")
            list_item.setCheckable(True)
            self.view.list_model().appendRow(list_item)

    def _populate_view(self):
        """ Use model data to populate view """
        courses = self.course_repo.courses().keys()
        self.view.course_combo().addItems(courses)

    def run(self, app: QApplication | None):
        logger.debug(f"Calling {self.run}")
        if app is not None:
            self.view.show()
            self.model.compile_thread.start()
            sys.exit(app.exec())
        else:
            self.model.compile_thread.start()
            self.view.show()

    def handle_dynamic_data(self):
        """ Flashcards must have a question and answer, however they may have other optional fields such as a proof or note
        This methods handles behaviour associated with the optional fields
        """
        if hasattr(self.model.current_card, SectionNames.PROOF.name): #type: ignore (fix?)
            self.view.show_proof_button().setHidden(False)
        else:
            self.view.show_proof_button().setHidden(True)

    def close(self):
        logger.info(f"Closing app")
        self.model.compile_thread.stop()

    def display_card(self, text_attr_name: str, path_attr_name: str):
        card = self.model.current_card
        if not card:
            self.view.set_error_message("No flashcard has been loaded")
            return
        text_attr = getattr(card, text_attr_name, None)
        path_attr =  getattr(card, path_attr_name, None) # TODO path_attr can be the value None, confusing to debug
        if text_attr is None or path_attr is None:
            logger.error(f"Flashcard does not have attr: {text_attr_name} or {path_attr_name}")
            self.view.set_error_message(f"Something went wrong: flashcard missing attribute(s) {text_attr_name} {path_attr_name}")
            return
        try:
            self.view.plot_tex(path_attr, text_attr)
        except LaTeXCompilationError as e:
            if len(text_attr) > 1000:
                text_attr = text_attr[:1001]
            logging.warning(f"Failed to compile card: {self.model.current_card} with tex: {text_attr}, {e}")

            self.view.set_error_message(f"Failed to compile flashcard question. Raw truncated latex: {text_attr}")

    def show_next_flashcard(self):
        logger.debug(f"Calling {self.show_next_flashcard}")
        try:
            self.model.next_flashcard()
            self.handle_dynamic_data()
            self.view.flashcard_type_label().setText(f"Section: {self.model.current_card.section_name.lower()}")
            #  TODO create some general method for handling additional info
        except FlashcardNotFoundException as e:
            logger.error(f"Failed to show next flashcard question, {e}")
            self.view.set_error_message(str(e))
        except LaTeXCompilationError as e:
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
        except LaTeXCompilationError as e:
            logger.error(f"Failed to compile prev flashcard question, {e}")
            self.view.set_error_message(str(e))
        self.display_card("question", "pdf_question_path")

    def show_flashcard_info(self):
        if self.model.current_card is None:
            message = "No flashcards have been loaded"
        else:
            tracked_string = self.model.current_card.question if self.view.document == self.model.current_card.pdf_question_path else self.model.current_card.answer

            if len(tracked_string) >= 300:
                tracked_string = tracked_string[:301]
            message = f"Source: {tracked_string.source}. Latex: {str(tracked_string)}"
        self.view.flashcard_info_button().set_message(message)

    def create_flashcards_from_file(self, path: Path, shuffle=False):
        section_names = [member for member in SectionNames]
        logger.info(f"Creating flashcards from {path}")
        load_thread = threading.Thread(target=self.model.load_flashcards, args=(section_names, [path], shuffle))
        load_thread.start()

    def create_flashcards(self):
        course_name, section_names, weeks, random = self.get_flashcard_pipeline_config()
        course = self.course_repo.get_course(course_name)

        # catch user errors
        if not section_names or not course:
            self.view.set_error_message(f"Invalid selection course={course}, section names={section_names}. You must select a course name and at least one section")
            logger.debug(f"Invalid selection (course={course}, section_names={section_names}) for generating flashcards")
            return
        paths = [lecture.path for lecture in course.lectures if course.get_week(lecture) in weeks]
        logger.info(f"Creating flashcards from {len(paths)} paths")
        load_thread = threading.Thread(target=self.model.load_flashcards, args=(section_names, paths, random))
        load_thread.start()

    def get_flashcard_pipeline_config(self) -> tuple[str, list[SectionNamesDescriptor], set[int], bool]:
        """ Retreives user config from widgets. We need to do error checking... what if no boxes are checked """
        random = self.view.random_checkbox().isChecked()
        course_name = self.view.course_combo().currentText()
        checked_sections = self._get_checked_items_from_listView(self.view.section_list())
        weeks_items = self._get_checked_items_from_listView(self.view.filter_by_week_list())
        weeks_text = [week.text() for week in weeks_items]
        # Clean filter by weeks params
        if "ALL" in [week.upper() for week in weeks_text] or not weeks_text:
            weeks = {i for i in range(1, 13+1)} # TODO: verify weeks
        else:
            weeks = {int(week.split(" ")[-1]) for week in weeks_text}

        # Clean checked section params
        section_names_pretty = [item.text().upper() for item in checked_sections]
        if "ALL" in [section.upper() for section in section_names_pretty]:
            section_names = [member for member in SectionNames]
        else:
            section_names = [member for member in SectionNames if member.name in section_names_pretty]
#            section_names = [getattr(SectionNames, section_pretty).value for section_pretty in section_names_pretty if hasattr(SectionNames, section_pretty)]
        return course_name, section_names, weeks, random

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

    # TODO
    def _get_pdf_source(self) -> str | None:
        card = self.model.current_card
        if card is None:
            return
        tracked_string = card.question if self.view.document == card.pdf_question_path else card.answer
        source = tracked_string.source
        return str(source)

    def open_main(self):
        course_name, *_ = self.get_flashcard_pipeline_config()
        course = self.course_repo.get_course(course_name)
        if course is not None:
            open_pdf(course.main_file)

    def launch_iterm(self):
        source = self._get_pdf_source()
        if source is not None:
            open_file_with_editor(source)



