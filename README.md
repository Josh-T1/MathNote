# Course Package
The course package provides an interface for quickly creating, compiling, adding images,
and doing basic parsing latex files. This functionality is accessed through the CLI;
running the `MathNote/course_cli.py` file *** change this *. 

# Gui Package
Responsible for creating and displaying flashcards containing material from course
lecture .tex files. In order for this to you must implement formatting of
lecture files. Flashcards can be created with the following 'sections':
definitions, theorems, and derivations. All sections must have the form
```
\{sectionName}{theoremName (thoerem) / word (defintion) / equality(derivation)}{
latex code
}
```
Theorem section have the additionaly allow for proofs. The parse will check and
see if a proof section follows the theorem and will display the first following
proof section if it exists. In order for this to work your notes must have the
form
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
\theorem{Pythagorean theorem}{
pythagonrean theorem statement
}
\pf{}{
pythagorean theorem proof
}
```
where the proof box is optional
TODO: Make sections configurable and what happens if None is places inside?



# Configuration
Projection configurations must be set `MathNote/config.json` before the project
us usable. 
- `note-path`: full path to directory containing math notes. It is assumed that
   all `courses` reside in the directory `{note-path}/{course (e.g math-445)}`. Further more
   lectures if created manually must reside in the directory
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

- `svg-gui-exec`: ** implement. Path to executable file responsible for starting
  your svg drawing software. I personally use a minimalistic vectors graphics
  PyQt6 application I built [include path clickable]. Inkscape is a far better
  alternative if speed is not a concer.

- `font`: ** not sure
- "`font-size`: ** not sure
- `export-dpi`: **
- `user-shortcuts-path`: **
- `.data` : **

#### Optional config
1. `shorcutmanager-logging-config`: standard python logging config
** defaults

