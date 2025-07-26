import argparse
import shutil
import sys
import logging
import logging.config
from pathlib import Path

from .controller import CourseCommand, FlashcardCommand, NoteCommand, NoteViewer
from .utils import config, config_dir, update_config


user_config_dir = config_dir()
root_dir = Path(config["root"])
note_dir = root_dir / "Notes"

def _initialize_config_tree():
    """ Create .config/mathnote directory with required subdirectories and files """
    user_config_dir.mkdir()
    (user_config_dir / "logs").mkdir()
    template_path = Path(__file__) / "templates/config_template.json"
    dest = user_config_dir / "config.json"
    shutil.copy(template_path, dest)

def _initialize_note_tree():
    """ Create MathNote/Notes directory with required subdirectories and files """
    note_macros, note_preamble = Path(config["note-macros"]), Path(config["note-preamble"])
    note_dir.mkdir()
    resourses_dir = note_dir / "resources"
    resourses_dir.mkdir()
    refs = resourses_dir / "refs.tex"
    refs.touch()
    shutil.copy(note_macros, resourses_dir / "macros.tex")
    shutil.copy(note_preamble, resourses_dir / "preamble.tex")

def _initialize_root_tree():
    """ Create MathNote directory with required subdirectories and files """
    macros, preamble = Path(config["macros"]), Path(config["preamble"])
    root_dir.mkdir()
    preambles_path = root_dir / "Preambles"
    preambles_path.mkdir()
    shutil.copy(macros, preambles_path / "macros.tex")
    shutil.copy(preamble, preambles_path / "preamble")
    _initialize_note_tree()


if not user_config_dir.is_dir():
    build = input(f"Configuration directory {user_config_dir} does not exist\nWould you like to create? (yn): ")
    if build == "y":
        print("Creating directory...")
        _initialize_config_tree()
    else:
        print("Command aborted. Directory must be created before proceeding")
        sys.exit()

if not (root := Path(config["root"])).is_dir():
    build = input(f"Mathnote directory {root} does not exist\nWould you like to create? (yn): ")
    if build == "y":
        print("Creating directory...")
        _initialize_root_tree()
    else:
        print("Command aborted. Directory must be created before proceeding")
        sys.exit()

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
            "level": config["log-level"],
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
global_parser = argparse.ArgumentParser(prog="mathnote", description="Cli for streamlining the note taking process")

subparsers = global_parser.add_subparsers(title="Subcommands", help="Note taking commands", dest="command")
course_parser = subparsers.add_parser("course", help="Create course file structure and inizialize course json file")
flashcard_parser = subparsers.add_parser("flashcard", help="Generate flashcards from .tex files")
note_parser = subparsers.add_parser("note", help="Create latex notes")
view_parser = subparsers.add_parser("view", help="View notes with gui in browser")

course_parser_arguments = [
        ("name",{"nargs": 1, "help": "Course name"}),
        ("-n", "--new-course", {"action": "store_true",
                            "help" :"Create new course and initialize directory. To automate initialization of course information, set '-u' flag"}),
        ("-i", "--information", {"action": "store_true",
                                 "help": "Displays course information"}), # seperate between private and public course info
        ("-u", "--user-input", {"action": "store_true",
                                "help": "Inizializes course_info.json through user input. Must be used with '--create' or '-c' flag"}),
        ("-o", "--open-main", {"action": "store_true",
                                "help": "Opens main.pdf in the course directory if it exists"}),
        ("-a", "--new-assignment", {"action": "store_true",
                                "help": "Create new assignment"}),
        ("-l", "--new-lecture", {"action": "store_true",
                                "help": "Creates new lecture file and prints path to stdout"}),
        ("-c", "--compile", {"action": "store_true", "help": ""})

        ]
note_parser_arguments = [
        ("--new-note", {"nargs": 1, "help": "create new note with 'name'"}),
        ("--new-category", {"nargs": 1, "help": "create new category with 'name'"}),
        ("-rm", "--remove-note", {"nargs": 1, "help": "remove note"}),
        ("-ls", "--list-notes", {"action": "store_true", "help": "list notes"}),
        ("-o", "--open-note", {"nargs": 1, "help": "open note"}),
        ("-c", "--compile-note", {"nargs": 1, "help": "compile note"}),
        ("-p", "--plot-network", {"action": "store_true", "help": "Displays network representation of notes"}),
        ("--rename", {"nargs": 2, "help": "rename note (old name, new name)"}),
        ("-t", "--tag" , {"nargs": 2, "help": "add tag to note (note name, tag)"}),
        ("--remove-tag", {"nargs": 1, "help": "remove tag from note"}),
        ("--exists", {"nargs": 1, "help": "returns true if note exists"}),
        ("--parent", {"nargs": 1, "default": [None], "help": "Sets note category to parent directory. Defaults to none"}),
        ("--note-type", {"nargs": 1, "default": ["typ"], "help": "Sets note category to parent directory. Defaults to none"}),
        ]

flashcard_parser_arguments = [
        ("-f", "--file", {"nargs": 1, "help": "Load flashcards from file path. Must be full path, or flag must be set with '-d'/'--dir'"}),
        ("-d", "--dir", {"nargs": 1, "help": "set current working directory"})
        ]


global_parser.add_argument("--update-config", action="store_true", help="Update macro and preamble files. If any macro or preamble files have been modified --this command must be run before changes take effect")
for arg in flashcard_parser_arguments:
    flashcard_parser.add_argument(*arg[:-1], **arg[-1])

for arg in course_parser_arguments:
    course_parser.add_argument(*arg[:-1], **arg[-1])

for arg in note_parser_arguments:
    note_parser.add_argument(*arg[:-1], **arg[-1])

args = global_parser.parse_args()


command_mapping = {
        "course": CourseCommand,
        "flashcard": FlashcardCommand,
        "note": NoteCommand,
        "view": NoteViewer
        }

def main():
    if args.update_config:
        update_config()

    elif args.command is None:
        global_parser.print_help()
        return
    else:
        instance = command_mapping[args.command](config)
        logger.info(f"Calling command {type(instance)}")
        instance.cmd(args)

if __name__ == '__main__':
    main()
