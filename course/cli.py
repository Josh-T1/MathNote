import argparse as arg
import subprocess
from course_controller import ClassCommand, LecCommand
from utils import get_config
import logging
# consider including last edited date for lectures?
logging.basicConfig(filename=__file__.rsplit("/", 1)[0] + "course.log")


global_parser = arg.ArgumentParser(prog="lecture", description="Set of commands for automating the note taking process in vim")
# open most recent lecture give the class name
# open to all class, only to classes that are currently active
#
subparsers = global_parser.add_subparsers(title="Subcommands", help="Note taking commands", dest="Subcommands")

class_parser = subparsers.add_parser("class", help="Create class file structure and inizialize corresponding class info json file")
class_parser.add_argument("name", nargs="?", help="Name of new class")
class_parser.add_argument("-c", "--create", action="store_true", help="Inizializes json file with user input otherwise a template json file is created")
class_parser.add_argument("-i", "--information", action="store_true", help="Displays class information") # seperate between private and public class info
class_parser.add_argument("-a", "--active", action="store_true", help="Opens a new latex lecture in the 'active' class if applicable")
#open_pdf_parser = subparsers.add_parser("View ")

file_parser = subparsers.add_parser("lec", help="Select lecture to open with nvim")
file_parser.add_argument("-n", "--lecture-name", action="store", default='active', help="Possible -n values: 'recent', 'active'(default), lecture path")
#file_parser.add_argument("-r", "--recent", action="store_true", help="Selects the most recent lecture")
#How does the script determine how and when debug file should be copied back into lecture file
file_parser.add_argument("-d", "--debug", action="store_true",
                         help="""Copy's lecture contents into a seperate file containing the required latex code to be compiled.
                                 When ___ the contents of the debug file are copied back into the orginal file""")
#file_parser.add_argument("-a", "--active", action="store_true", help="Open lecture for active class")




view_parser = subparsers.add_parser("tex", help="")
#view_parser.add_argument("-n", "--name", action="store", default="recent")
#view_parser.add_argument("-o", action="store", default)

#                                1.'recent' -> (default) opens pdf corresponding to the class with the most recently edited lecture
#                                2. compile
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
