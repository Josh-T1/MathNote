import argparse
import shutil
import sys
import logging
import logging.config

from .cmd import NoteViewer
from .config import CONFIG


user_config_dir = CONFIG.config_dir()

def _initialize_config_tree():
    """
    Initialize .config/MathNote directory with required subdirectories and files
    {config_dir}/
                cache/pdf/
                Typst/*typst_templates
                LaTeX/*latex_templates
                config.json

    """
    logger.debug(f"Building config tree at {user_config_dir}")
    user_config_dir.mkdir()
    (user_config_dir / "logs").mkdir()
    CONFIG.cache_dir().mkdir()
    (CONFIG.cache_dir() / "pdf").mkdir()
    user_typst_dir = user_config_dir / "Typst"
    user_latex_dir = user_config_dir / "LaTeX"
    user_typst_dir.mkdir()
    user_latex_dir.mkdir()
    (user_config_dir / "LaTeX").mkdir()
    config_template_path = CONFIG.templates_path / "config_template.json"
    typst_template_dir = CONFIG.templates_path / "Typst"
    latex_template_dir = CONFIG.templates_path / "LaTeX"
    dest = user_config_dir / "config.json"
    shutil.copy(config_template_path, dest)
    shutil.copytree(typst_template_dir, user_typst_dir)
    shutil.copytree(latex_template_dir, user_latex_dir)

def _initialize_project_tree():
    """
    Create MathNote directory with required subdirectories and files

    {root_path}/
                Preambles/*tex_preambles
                NoteRepositories/
                Decks/
                Courses/
    """

    if not CONFIG.root_path.is_dir():
        logger.debug(f"Creating project root at {CONFIG.root_path}")
        CONFIG.root_path.mkdir()

    logger.debug(f"Building project tree at {CONFIG.root_path}")
    preambles_path = CONFIG.root_path / "Preambles"
    preambles_path.mkdir()
    shutil.copytree(CONFIG.templates_path, preambles_path, dirs_exist_ok=True)

    CONFIG.note_repo_dir.mkdir()
    CONFIG.decks_dir.mkdir()
    CONFIG.courses_dir.mkdir()




logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {},

    "formatters": {
        "simple": {
            "format": "[%(asctime)s][%(levelname)s][%(name)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },

    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": CONFIG.log_level,
            "formatter": "simple",
            "filename": str(user_config_dir / "logs/mathnote.log"),
            "maxBytes": 1000000,
            "backupCount": 2
            }
        },

    "loggers": {
        "mathnote": {
            "level": "DEBUG",
            "handlers": ["file"]
        }
    }
}


logging.config.dictConfig(config=logging_config)
logger = logging.getLogger("mathnote")


def main():
    global_parser = argparse.ArgumentParser(prog="mathnote", description="Cli for streamlining the note taking process")
    args = global_parser.parse_args()
    if not user_config_dir.is_dir():
        build = input(f"Configuration directory {user_config_dir} does not exist\nWould you like to create? (yn): ")
        if build == "y":
            _initialize_config_tree()
        else:
            logger.error("Failed to build config directory tree")
            sys.exit()

    if not CONFIG.root_path.is_dir():
        build = input(f"Mathnote directory {CONFIG.root_path} does not exist\nWould you like to create? (yn): ")
        if build == "y":
            _initialize_project_tree()
        else:
            print("Failed to build project directory tree")
            sys.exit()

    logger.debug(f"Calling command {NoteViewer}")
    view = NoteViewer()
    view.cmd(args)

if __name__ == '__main__':
    main()
