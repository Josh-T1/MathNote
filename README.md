# Project Description

## TODO
- Finish writing documentation
- Re organize cli interface. We currently have `main_gui.py` and `main_cli.py`.
  Would probably make much more sense to merge `main_gui.py` into `main_cli.py`.
  In addition much of the functionality of `main_cli.py` was poorly thought out
  and as a result needs some serious re working.
- Write tests... This entire package is untested for the most part.
- Delete `shortcuts` package... This was a poor attempt at implementing
  shortcuts for Inkscape. Realized it is much easier to create a minimalistic
  vector graphics editor and use that for in class drawing.

## Course Package
The course package provides an interface for quickly creating, compiling, adding images,
and doing basic parsing of latex files. This functionality is accessed through the CLI;
running the `MathNote/course_cli.py` file --change this . 

## Gui Package
Responsible for creating and displaying flashcards containing material from course
lecture .Tex files. In order to use this to package you must implement specific formatting of
lecture files. Flashcards can be created with the following 'sections':
definitions, theorems, and derivations. All sections must have the form
```
\{sectionName}{theoremName (thoerem) / word (defintion) / equality(derivation)}{
latex code
}
```
Theorem sections additionally allow for proofs to be displayed as flashcard
answers along side the statement. The latex parser will check and
see if a proof section follows the theorem; displaying the first following
proof section if it exists. Proof boxes must be of the form:
```
\{sectionName}{theoremName (thoerem) / word (defintion) / equality(derivation)}{
latex code
}
\{proofSectionName}{any (not displayed on flashcard but must be included)}{
latex code
}
```
For example suppose `"TODO: {"theorem": "theo", "proof": "pf"}"` is set in the
config file, then all theorems in .tex files must follow the format
```
\theo{Pythagorean theorem}{
pythagonrean theorem statement
}
\pf{}{
pythagorean theorem proof
}
```
where the proof box is optional
TODO: Make sections configurable and what happens if None is places inside?



# Configuration
Any directory under under the `note-path` (see config.json setup section) with a 
`course_info.json` file will be detected as course.

## Config.json file setup
Projection configurations must be set `MathNote/config.json` before the project
us usable. 
- `note-path`: full path to directory containing math notes. It is assumed that
   all `courses` reside in the directory `{note-path}/{course (e.g math-445)}`. 
   Further more lectures if created manually must reside in the directory
   `{note-path}/course_dir/lectures`. When using the CLI this is default
   behaviour.
- `lecture-template`: path to latex template used for lectures (is this even
  used?)

- `main-template`: Full path to main file template. Main file refers to the file
  responsible for combining all lectures into one latex file. There is a default
  template in `MathNote/templates`, however other templates can be specified
- `macros-path`: Full path to macros.tex file if relevant. This file specifies
  all user defined commands. 
- `macro-name`: List of names all commands defined in macros.tex where each name
  excluded backslash. Unfortunate there is no way to do this more dynamically at
  the moment.** Check code for specific requirement regarding valid user
  commands. There is currently no system to parse more complex commands and as a
  result all commands following a different format must be removed prior to
  using this package. 



- `font`: ** not sure
- "`font-size`: ** not sure
- `export-dpi`: **
- `user-shortcuts-path`: **
- `.data` : **

#### Optional config
1. `shorcutmanager-logging-config`: standard python logging config
** defaults
- `svg-gui-exec`: ** implement. Command to open vector graphics editor or path to executable responsible for opening editor.
Inkscape a great open source vector graphics editor, alternatively you could use
my other project [[]] if you want a faster minimalistic option. Note this
project has not been finished and has several undesirable side effect and lacks
basic options

#### Drawing config
- 
