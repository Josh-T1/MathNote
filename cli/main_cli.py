import argparse as arg
from course_controller import ClassCommand, LecCommand
from utils import get_config
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
file_parser = subparsers.add_parser("lec", help="Select lecture to open with nvim or 'debug'")
tex_parser = subparsers.add_parser("tex", help="TODO")

class_parser_arguments = [
        ("name",{"nargs": "?",
                 "help": "Name of new class"}),
        ("-c", "--create", {"action": "store_true",
                            "help" :"Inizializes json file with user input otherwise a template json file is created"}),
        ("-i", "--information", {"action": "store_true",
                                 "help": "Displays class information"}), # seperate between private and public class info
        ("-a", "--active", {"action": "store_true", "help": "Opens a new latex lecture in the 'active' class if applicable"}),
        ("-u", "--user-input", {"action": "store_true",
                                "help": "Inizializes course_info.json through user input"}),
        ]
# At some point I will realize that debug and clean are useless and that I should make file_parser, tex_parser into one
file_parser_arguments = [
        ("name", {"nargs": "?", "action": "store", "default": 'active',
                  "help": "Possible values: 'recent', 'active'(default), 'class name'"}),
        ("-d", "--debug", {"action": "store_true",
                           "help": """Copy's lecture contents into a seperate file containing the required latex code to be compiled.
                           How is this dir clearned and file move back? Who the fuck knows"""}),
        ("-c", "--clean", {"action": "store_true",
                           "help": """Takes body of debug-lecture(s) and replaces their corresponding lecture contents,
                           then contents in the directory are deleted, defaults to all files in debug dir"""})
        ]

tex_parser = [
        ("name", {"nargs": "?", "action": "store", "default": 'active',
                  "help": "file path, class name, or directory path. Relative of full paths"}),
        ("-d", "--directory", {"action": "store_true", "help": "Use flag if you would like to parse all files in directory"}),
        ("-f", "--file", {"action": "store_true", "help": "Use flag if you would like to parse file with 'name'"}),
        ("-c", "--compile", {"action": "store_true", "help": "Compile main.tex, name must be name of class"})
        ]

for arg in class_parser_arguments:
    class_parser.add_argument(*arg[:-1], **arg[-1])

for arg in file_parser_arguments:
    file_parser.add_argument(*arg[:-1], **arg[-1])

args = global_parser.parse_args()

command_mapping = {
        "class": ClassCommand,
        "lec": LecCommand,
        }

def main():
    config = get_config()
    instance = command_mapping[args.Subcommands](config)
    instance.handle_cmd(args)

if __name__ == '__main__':
    main()
