from pathlib import Path
import threading
import time
import logging
import random

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QListView, QMainWindow

from .ui_utils import with_error_dialog
from ..flashcard_navbar import FlashcardNavbar
from ..dialog import NameDialog, NewTypesetFileDialog, confirm_delete
from ..flashcard_viewer import FlashcardView
from ...models import FlashcardSideName
from ...services import (CourseRepository, FlashcardSession, FlashcardCache, FlashcardCompiler, open_pdf, DeckRepository,
                         DataGenerator, FlashcardBuilderStage, CleanStage, DataGenerator, ProcessingPipeline, FormatStage)

from ...config import CONFIG, MACROS, Section
from ...exceptions import FlashcardCompilationError



logger = logging.getLogger(__name__)





class FlashcardController:
    def __init__(self, window: QMainWindow, navbar: FlashcardNavbar, view: FlashcardView):
        super().__init__()
        self.window = window
        self.navbar = navbar
        self.view = view
        self.deck_repo = DeckRepository(CONFIG)
        self.cache = FlashcardCache(CONFIG.cache_dir())
        self.compiler = FlashcardCompiler(self.cache)
        self.session = FlashcardSession(self.compiler)
        self.course_repo = CourseRepository(CONFIG)

        self.set_handlers()
        self._populate_view()


    def set_handlers(self):
        self.view.btn_bar.next_flashcard_button.clicked.connect(lambda: self.show_next_flashcard())
        self.view.btn_bar.prev_flashcard_button.clicked.connect(lambda: self.show_prev_flashcard())
        self.navbar.create_cards_btn.clicked.connect(lambda: self.create_flashcards())
        self.view.info_bar.info_button.clicked.connect(lambda: self.show_flashcard_info())
        self.navbar.course_config.update_filters.connect(lambda: self.handle_update_filters())
        self.session.pos.connect(lambda x, y: self.handle_update_count(x, y))
        self.navbar.deck_config.new_deck_btn.clicked.connect(lambda: self.handle_new_deck())
        self.navbar.deck_config.trash_btn.clicked.connect(lambda: self.handle_delete_deck())
        self.navbar.deck_config.rename_btn.clicked.connect(lambda: self.handle_rename_deck())

    @with_error_dialog
    def handle_rename_deck(self):
        curr_name = self.navbar.deck_config.deck_combo.currentText()
        idx = self.navbar.deck_config.deck_combo.currentIndex()
        dialog = NameDialog()
        if not dialog.exec():
            return
        new_name = dialog.get_data()
        self.deck_repo.rename_deck(curr_name, new_name)
        self.navbar.deck_config.deck_combo.setItemText(idx, new_name)

    @with_error_dialog
    def handle_delete_deck(self):
        name = self.navbar.deck_config.deck_combo.currentText()
        idx = self.navbar.deck_config.deck_combo.currentIndex()
        delete = confirm_delete(self.window, name)
        if not delete:
            return
        self.deck_repo.delete_deck(name)
        self.navbar.deck_config.deck_combo.removeItem(idx)


    @with_error_dialog
    def handle_new_deck(self):
        dialog = NewTypesetFileDialog()
        if not dialog.exec():
            return
        name, ftype = dialog.get_data()
        self.deck_repo.new_deck(name, ftype)
        self.navbar.deck_config.deck_combo.addItem(name)
        self.navbar.deck_config.deck_combo.setCurrentIndex(self.navbar.deck_config.deck_combo.count() - 1)


    @with_error_dialog
    def handle_update_filters(self):
        text = self.navbar.course_config.course_combo.currentText()
        course = self.course_repo.get_course(text)
        if course is None:
            raise ValueError("Course directory not found")

        model = self.navbar.course_config.filter_by_lecture_list_model
        model.clear()
        all_box = QStandardItem('All')
        all_box.setCheckable(True)
        model.appendRow(all_box)
        for i in range(1, len(course.lectures) + 1):
            list_item = QStandardItem(f"Lecture {i}")
            list_item.setCheckable(True)
            model.appendRow(list_item)



    @with_error_dialog
    def show_next_flashcard(self, first=False):
        card = self.session.next_flashcard(first=first)
        try:
            self.view.display_compiled_card(card)
        except Exception as e:
            ans = card.sides.get(FlashcardSideName.ANSWER)
            pf = card.sides.get(FlashcardSideName.PROOF)

            if ans is None and pf is None:
                question = card.sides[FlashcardSideName.QUESTION].content
                raise ValueError(f"Missing second side\n Flashcard question: {question}\n source: {question.source}")

            if ans is not None and ans.pdf_path is None:
                ans.pdf_path = self.compiler.text_to_pdf(str(ans.content))

            if pf is not None and pf.pdf_path is None:
                pf.pdf_path = self.compiler.text_to_pdf(str(pf.content))

            self.view.display_compiled_card(card)
            raise FlashcardCompilationError("Failed to compile flashcard. Displaying raw LaTeX/Typst")


    def handle_update_count(self, current: int, total: int):
        self.view.info_bar.set_count(current, total)


    @with_error_dialog
    def show_prev_flashcard(self):
        logger.debug(f"Calling {self.show_prev_flashcard}")
        card = self.session.prev_flashcard()
        self.view.display_compiled_card(card)

    def show_flashcard_info(self):
        card = self.session.current_card
        if card is None:
            message = "No flashcards have been loaded"
            self.view.info_bar.info_button.set_message(message)
            return

        info = card.sides[FlashcardSideName.QUESTION].content.source
        if info is None:
            message = "No flashcards have been loaded"
            return
        else:
            message = f"Source: {info}"
        self.view.info_bar.info_button.set_message(message)

    def create_flashcards(self):
        if self.navbar.stack.currentWidget() == self.navbar.course_config:
            paths, section_names_dict, shuffle = self.generate_pipe_course_config()
            logger.info(f"Creating flashcards from {len(paths)} paths")
        else:
            path, section_names_dict, shuffle = self.generate_pipe_deck_config()
            paths = [path]

        macros = MACROS.parse_macros()
        data_iterable = DataGenerator(paths)
        clean_data_stage = CleanStage(macros)
        format_state = FormatStage()
        build_stage = FlashcardBuilderStage(section_names_dict)
        # TODO
        build_stage.add_subsection_finder("Proof")
        pipeline = ProcessingPipeline(data_iterable)
        pipeline.add_stage(clean_data_stage)
        pipeline.add_stage(build_stage)
        pipeline.add_stage(format_state)

        load_thread = threading.Thread(target=self.session.load_flashcards, args=(pipeline, shuffle))
        load_thread.start()

        time.sleep(0.1)
        self.show_next_flashcard(first=True)

    def stop(self):
        self.session.stop()

    def generate_pipe_deck_config(self) -> tuple[Path, dict[str, Section], bool]:
        filename = self.navbar.deck_config.deck_combo.currentText()
        path = self.deck_repo.decks.get(filename)
        if path is None:
            raise ValueError("Deck with name '{filename}' is not recognized")

        shuffle = self.navbar.deck_config.random_checkbox.isChecked()
        checked_sections = self._get_checked_items_from_listView(self.navbar.deck_config.section_list.section_list)
        section_names_pretty = [item.text().upper() for item in checked_sections]
        if "ALL" in [section.upper() for section in section_names_pretty]:
            section_names = CONFIG.section_names
        else:
            section_names = {k: d for (k, d) in CONFIG.section_names.items() if k in section_names_pretty}
        return path, section_names, shuffle

    def generate_pipe_course_config(self) -> tuple[list[Path], dict[str, Section], bool]:
        """ Retreives user config from widgets. We need to do error checking... what if no boxes are checked """
        # Lecture numberes
        course_name = self.navbar.course_config.course_combo.currentText()
        course = self.course_repo.get_course(course_name)
        if not course:
            raise ValueError(f"Course name {course} not recognized")
        lec_list_items = self._get_checked_items_from_listView(self.navbar.course_config.filter_by_lecture_list)
        lec_text_items = [lec.text() for lec in lec_list_items]
        if "ALL" in [lec.upper() for lec in lec_text_items] or not lec_text_items:
            lectures = {i for i in range(1, len(course.lectures))}
        else:
            lectures = {int(lecture.split(" ")[-1]) for lecture in lec_text_items}

        # Sections
        checked_sections = self._get_checked_items_from_listView(self.navbar.course_config.section_list.section_list)
        section_names_pretty = [item.text().upper() for item in checked_sections]
        if "ALL" in [section.upper() for section in section_names_pretty]:
            section_names = CONFIG.section_names
        else:
            section_names = {k: d for (k, d) in CONFIG.section_names.items() if k in section_names_pretty}

        # Filter paths and shuffle
        shuffle = self.navbar.course_config.random_checkbox.isChecked()
        paths = [lecture.path for lecture in course.lectures if lecture.number() in lectures]
        if shuffle:
            random.shuffle(paths)

        return paths, section_names, shuffle

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

    def open_main(self):
        course_name = self.navbar.course_config.course_combo.currentText()
        course = self.course_repo.get_course(course_name)
        if not course:
            raise ValueError(f"Course name {course} not recognized")
        open_pdf(course.main_file)

    def _populate_view(self):
        courses = self.course_repo.courses().keys()
        self.navbar.course_config.course_combo.addItems(courses)
        keys = ["All"]
        keys.extend([name.lower().capitalize() for name in list(CONFIG.section_names.keys())])
        self.navbar.course_config.section_list.add_items(keys)
        self.navbar.deck_config.section_list.add_items(keys)
        self.navbar.deck_config.deck_combo.addItems(list(self.deck_repo.decks.keys()))

