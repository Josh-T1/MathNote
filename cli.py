import argparse
from .controller import CourseCommand, FlashcardCommand, NoteCommand
from .global_utils import get_config
import logging
import logging.config
from .global_utils import get_config
from pathlib import Path

config = get_config()
logging_config = config["logging-config"]
logging.config.dictConfig(config=logging_config)
logger = logging.getLogger("cli")
global_parser = argparse.ArgumentParser(prog="lecture", description="Cli with commands for automating the note taking process")

subparsers = global_parser.add_subparsers(title="Subcommands", help="Note taking commands", dest="command")
course_parser = subparsers.add_parser("course", help="Create course file structure and inizialize course json file")
flashcard_parser = subparsers.add_parser("flashcard", help="Generate flashcards from .tex files")
note_parser = subparsers.add_parser("note", help="Create latex notes")

course_parser_arguments = [
        ("name",{"nargs": "?",
                 "help": "Name of new course"}),
        ("-n", "--new-course", {"action": "store_true",
                            "help" :"Create new course and initialize directory. To automate initialization of course information see '-u' flag"}),
        ("-i", "--information", {"action": "store_true",
                                 "help": "Displays course information"}), # seperate between private and public course info
        # get read of this
#        ("-c", "--current-course", {"action": "store_true",
#                            "help": "Opens a new latex lecture in the 'active' course if applicable"}),
        ("-u", "--user-input", {"action": "store_true",
                                "help": "Inizializes course_info.json through user input. Must be used with --create -c flag"}),
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
        ("-s", "--search", {"nargs": "store_true", "help": "search through notes"})
        ]

flashcard_parser_arguments = [
        ("-f", "--file", {"nargs": 1, "help": "Load flashcards from file path. Must be full path, or flag must be set with '-d'/'--dir'"}),
        ("-d", "--dir", {"nargs": 1, "help": "set current working directory"})
        ]

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

def validate() -> bool:
    valid = True
    paths = {"note-path": config.get("note-path", "missing key, value pair"),
             "main-template": config.get("main-template", "missing key, value pair")
             }
    for path_name, path in paths.values():
        if not Path(path).is_dir():
            print(f"Invalid {path_name} specified in config.json: {path}")
            valid = False
    return valid

def main():
    valid = validate()
    if not valid:
        quit()

    if args.command is None:
        global_parser.print_help()
        return

    config = get_config()
    instance = command_mapping[args.command](config)
    logger.info(f"Calling command {type(instance)}")
    instance.cmd(args)

if __name__ == '__main__':
    main()
