import argparse as arg
from re import sub

# consider including last edited date for lectures?

global_parser = arg.ArgumentParser(prog="lecture",
                            description="Set of commands for automating the note taking process in vim",
                            )
# open most recent lecture give the class name
# open to all class, only to classes that are currently active
#
subparsers = global_parser.add_subparsers(title="Subcommands", help="Note taking commands")
class_parser = subparsers.add_parser("class", help="Create class file structure and inizialize corresponding class info json file")
class_parser.add_argument("-n", "--name", action="store", help="Name of new class")
class_parser.add_argument("-c", "--create", help="Inizializes json file with user input otherwise a template json file is created")
class_parser.add_argument("-i", "--information", nargs=1, action="store", default="all", help="Displays class information") # seperate between private and public class info
#open_pdf_parser = subparsers.add_parser("View ")

file_parser = subparsers.add_parser("lec", help="Select lecture to open with nvim")
file_parser.add_argument("-n", "--name", action="store", default='all', help="Filter lectures by class name")
file_parser.add_argument("-r", "--recent", action="store_true", help="Selects the most recent lecture")
#How does the script determine how and when debug file should be copied back into lecture file
file_parser.add_argument("-d", "--debug", action="store_true",
                         help="""Copy's lecture contents into a seperate file containing the required latex code to be compiled.
                                 When ___ the contents of the debug file are copied back into the orginal file""")

file_parser.add_argument("-a", "--active", action="store_true", help="Opens a new latex lecture in the 'active' class if applicable")



view_parser = subparsers.add_parser("tex", help="Compliles main.tex for the specified class and open main.pdf file")
view_parser.add_argument("-n", "--name", action="store", default="recent",
                         help="""Available options are:
                                1.'recent' -> (default) opens pdf corresponding to the class with the most recently edited lecture
                                2. 'name' -> name of target class pdf
                                3. 'active' -> class that is currently acitve if applicable, falls back on most recent""")

global_parser.parse_args()




if __name__ == '__main__':
    print(args.create_class)
