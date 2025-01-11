import argparse
import shutil
from .controller import CourseCommand, FlashcardCommand, NoteCommand
from .utils import config, config_dir
import logging
import logging.config
from pathlib import Path
import json

user_config_dir = config_dir()

def initialize():
    """ Create .config/mathnote directory with required subdirectories and files """
    user_config_dir.mkdir()
    (user_config_dir / "logs").mkdir()
    template_path = Path(__file__) / "templates/config_template.json"
    dest = user_config_dir / "config.json"
    shutil.copy(template_path, dest)

if not user_config_dir.is_dir():
    initialize()

config_path =Path(__file__).parent  / "logging_config.json"
with open(config_path) as f:
    logging_config = json.load(f)


logging_config["handlers"]["file"]["filename"] = str(user_config_dir / "logs/mathnote.log")
logging_config["loggers"]["mathnote"]["level"] = config["log-level"]

logging.config.dictConfig(config=logging_config)
logger = logging.getLogger("mathnote")
global_parser = argparse.ArgumentParser(prog="mathnote", description="Cli for streamlining the note taking process")

subparsers = global_parser.add_subparsers(title="Subcommands", help="Note taking commands", dest="command")
course_parser = subparsers.add_parser("course", help="Create course file structure and inizialize course json file")
flashcard_parser = subparsers.add_parser("flashcard", help="Generate flashcards from .tex files")
note_parser = subparsers.add_parser("note", help="Create latex notes")

course_parser_arguments = [
        ("name",{"nargs": "?",
                 "help": "Name of new course"}),
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
        ("-n", "--new-note", {"nargs": 1, "help": "create new note"}),
        ("-rm", "--remove-note", {"nargs": 1, "help": "remove note"}),
        ("-ls", "--list-notes", {"action": "store_true", "help": "list notes"}),
        ("-o", "--open-note", {"nargs": 1, "help": "open note"}),
        ("-c", "--compile-note", {"nargs": 1, "help": "compile note"}),
        ("--rename", {"nargs": 2, "help": "rename note"}),
        ("-t", "--tag" , {"nargs": 2, "help": "add tag to note"}),
        ("--remove-tag", {"nargs": 1, "help": "remove tag from note"}),
        ("--exits", {"nargs": 1, "help": "returns true if note exists"}),


        ]

flashcard_parser_arguments = [
        ("-f", "--file", {"nargs": 1, "help": "Load flashcards from file path. Must be full path, or flag must be set with '-d'/'--dir'"}),
        ("-d", "--dir", {"nargs": 1, "help": "set current working directory"})
        ]


global_parser.add_argument("--update-config", action="store_true", help="Update configuration files. If any template or config files have been modified --this command must be run before changes take effect")
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
        "note": NoteCommand
        }


def main():
    if args.command is None:
        global_parser.print_help()
        return

    instance = command_mapping[args.command](config)
    logger.info(f"Calling command {type(instance)}")
    instance.cmd(args)

if __name__ == '__main__':
    main()
