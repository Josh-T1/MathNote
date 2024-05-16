# Motivation
This prject consists of two main parts


# Configuration
In the folder `mathnote` there is a `config.json` file which stores project
configuration information such as the target directory for storing notes and 
latex templates, where all paths are required to be complete paths. The
`lecture-template` and `main-template` fields store the complete path to the
'debug' and 'main' files respectively. The latex `\input{}` command uses
relative path from the project file. Assuming that there is only one of both a `macros.tex`
and `preamble.tex` file located in the course notes root directory, the debug and
main file templates include different relative paths to those file. More
information on the 'debug' file is included in the course module information
section

# Course Module
The course module implements a command line interface with several subcommands.
* Include bash code




