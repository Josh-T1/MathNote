import argparse
from .controller import ClassCommand, FlashcardCommand
from .global_utils import get_config
import logging
import logging.config
from .global_utils import get_config


logging_config = get_config()["logging-config"]
logging.config.dictConfig(config=logging_config)
logger = logging.getLogger("cli")
global_parser = argparse.ArgumentParser(prog="lecture", description="Cli with commands for automating the note taking process")

subparsers = global_parser.add_subparsers(title="Subcommands", help="Note taking commands", dest="command")
class_parser = subparsers.add_parser("class", help="Create class file structure and inizialize class json file")
flashcard_parser = subparsers.add_parser("flashcard", help="Generate flashcards from .tex files")

class_parser_arguments = [
        ("name",{"nargs": "?",
                 "help": "Name of new class"}),
        ("-n", "--new-course", {"action": "store_true",
                            "help" :"Create new class and initialize directory. To automate initialization of course information see '-u' flag"}),
        ("-i", "--information", {"action": "store_true",
                                 "help": "Displays class information"}), # seperate between private and public class info
        ("-c", "--current-course", {"action": "store_true",
                            "help": "Opens a new latex lecture in the 'active' class if applicable"}),
        ("-u", "--user-input", {"action": "store_true",
                                "help": "Inizializes course_info.json through user input. Must be used with --create -c flag"}),
        ("-o", "--open-main", {"action": "store_true",
                                "help": "Opens main.pdf in the course directory if it exists"}),
        ("-a", "--new-assignment", {"action": "store_true",
                                "help": "Create new assignment"}),
        ("-l", "--new-lecture", {"action": "store_true",
                                "help": "Creates new lecture file and prints path to stdout"}),
        ]


# add m option for compilling and opening mainfile
flashcard_parser_arguments = [
        ("-f", "--file", {"nargs": 1, "help": "Load flashcards from file path. Must be full path, or flag must be set with '-d'/'--dir'"}),
        ("-d", "--dir", {"nargs": 1, "help": "set current working directory"})
        ]

for arg in flashcard_parser_arguments:
    flashcard_parser.add_argument(*arg[:-1], **arg[-1])

for arg in class_parser_arguments:
    class_parser.add_argument(*arg[:-1], **arg[-1])

args = global_parser.parse_args()


command_mapping = {
        "class": ClassCommand,
        "flashcard": FlashcardCommand,
        }

def main():
    if args.command is None:
        global_parser.print_help()
        return

    config = get_config()
    instance = command_mapping[args.command](config)
    logger.info(f"Calling command {type(instance)}")
    instance.cmd(args)

if __name__ == '__main__':
    main()
