import argparse as arg
from course.controller import ClassCommand, LecCommand
from .global_utils import get_config
import logging

LEVEL = logging.DEBUG
cwd = __file__.rsplit("/", 1)[0]
logging.basicConfig(
        level=LEVEL,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        filename=cwd+"/course.log"
        )

global_parser = arg.ArgumentParser(prog="lecture", description="Set of commands for automating the note taking process in vim")

subparsers = global_parser.add_subparsers(title="Subcommands", help="Note taking commands", dest="Subcommands")

class_parser = subparsers.add_parser("class", help="Create class file structure and inizialize class json file")
flashcard_parser = subparsers.add_parser("flashcard", help="Generate flashcards from .tex files")

class_parser_arguments = [
        ("name",{"nargs": "?",
                 "help": "Name of new class"}),
        ("-c", "--create", {"action": "store_true",
                            "help" :"Inizializes json file with user input otherwise a template json file is created"}),
        ("-i", "--information", {"action": "store_true",
                                 "help": "Displays class information"}), # seperate between private and public class info
        ("-a", "--active", {"action": "store_true",
                            "help": "Opens a new latex lecture in the 'active' class if applicable"}),
        ("-u", "--user-input", {"action": "store_true",
                                "help": "Inizializes course_info.json through user input. Must be used with --create -c flag"}),
        ]
# add m option for compilling and opening mainfile

for arg in class_parser_arguments:
    class_parser.add_argument(*arg[:-1], **arg[-1])


args = global_parser.parse_args()

command_mapping = {
        "class": ClassCommand,
        "flashcard": LecCommand,
        }

def main():
    config = get_config()
    instance = command_mapping[args.Subcommands](config)
    instance.handle_cmd(args)

if __name__ == '__main__':
    main()
