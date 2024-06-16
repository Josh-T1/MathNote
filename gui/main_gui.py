from PyQt6.QtWidgets import QApplication
from .controller import FlashcardController
from .window import MainWindow
from .flashcard_model import FlashcardModel, TexCompilationManager
import logging
import logging.config
from ..global_utils import get_config


config = get_config()
logging.config.dictConfig(config = config["flashcard-logging-config"])
logger = logging.getLogger(__name__)

def main():
    app = QApplication([])
    compilation_manager = TexCompilationManager()
    flashcard_model = FlashcardModel(compilation_manager)
    window = MainWindow()
    controller = FlashcardController(window, flashcard_model, config)
    window.setCloseCallback(controller.close)
    controller.run(app)
    if not flashcard_model.compile_thread.stopped(): # Cant remember if I actually need this
        flashcard_model.compile_thread.wait_for_stop()

if __name__ == '__main__':
    main()

