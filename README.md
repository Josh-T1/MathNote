# MathNote
![flashcard](assets/flashcard.png)

This package enhances the LaTex note taking experience by simplifying the organizational process associated
with taking latex lecture notes, enabling the generation of flashcards from lectures notes, and providing a management
system for notes-- from which you can generate interactive networks for better visualization.
The command line interface has three main commands:

1. `course`: command used for setting up the directory structure, getting course information, and other housekeeping tasks
2. `flashcard`: used to generate pdf flashcards, parsed from tex files
3. `note`: used for creating and managing short notes.

## Flashcard
Usage: 
* `flashcard [-flag]`

Flags:
* `-f`, `--file`: Load flashcards from file. Must provide full path as flag argument
* `-d`, `--dir`: Set current working directory: TODO


The `flashcard` command requires lecture notes to follow fairly strict formatting. In order to generate flashcards
from a tex file, all relevant definitions, theorems, and other sections, must be contained in their own
"namespace", having the syntax
```
\sectionName{ ... }{
latex code
}
```
where sectionName would be one of: "definition, "theorem", "proof", ect.
Additionally theorem/lemma/proposition flashcards, by default include the proof as an additional "answer". Note that theorem/lemma/proposition
section flashcards will only have a corresponding proof when directly followed by a proof section in the Tex file.
For example:
```
\theo{Pythagorean theorem}{
pythagonrean theorem statement
}
\pf{}{
pythagorean theorem proof
}
```
Any Tex file following the above syntactic rules can be parsed into flashcards-- my personal
approach has been to define a `\newtcbtheorem` environment for each section in the preamble. For example suppose
you have defined the `\newtcbtheorem` section "Theorem". I would then include the following command in macros.tex
```tex
\newcommand{\theo}[2]{\begin{Theorem*}{#1}{}#2\end{Theorem*}}
```
This allows you to write theorems (or any section) using the syntactic rules defined earlier.
All sections must be specified in the configuration file, for more details look [configuration](#configuration). 



## Course
Usage:
* `course {name} [-flag]`

Arguments:
* {name}     Name of course, e.g math-445

Flags:
* `-n`, `--new-course`: Initializes new course directory, to automate initialization set `-u` flag
* `-i`, `--information`: Display class information
* `-c`, `--current-course`: DEL: TODO
* `-u`, `--user-input`: Initializes course.json through user input
* `-o`, `--open-main`: Opens main.pdf file corresponding to course
* `-a`, `--new-assignment`: Create new assignment under `{course}/assignments/`
* `-l`, `--new-lecture`: Creates new lecture file and prints file path to stdout

When a new course is created, the following directories are created under `NewCourse`
```
root/
├── preamble.tex
├── macros.tex
│
└── NewCourse/              # New course directory
     ├── main/    
     │   ├── main.tex
     │   └── lectures/
     │
     ├── resources/         # external resources included in main.tex (e.g figure.svg)
     ├── assignments/       # default location for assingments when created using 'course' cmd
     ├── problems/
     └──course_info.json    # course configuration and information

```



### Compilation
You can use the `-c` flag to compile your note from the command line, however if you use 
`VimTex`, then you must add the following to your `nvim` configuration
```lua

```


## Note
Usage:
* `note {name} [-flags]`
Arguments:
* name          name of note being created or opened
Flags:
* `-e`, `--edit`
* `-c`, `--compile`
This command is a work in progressive. Typically 


# Dependencies
-tlmgr
-latekmk

This package has been tested on MacOS (still experimental), however it remains untested on other operating systems (should work on Windows and Linux).

There are several non critical dependencies (in addition to those in requirements.txt) that are required
for the app to fully function. 
1. `iTerm`: The flashcard gui has a button for opening the Tex file corresponding to the current flashcard, in a new iTerm2
session using the `vim` editor. If you wish to use a different terminal emulator or editor,
you must modify the functions `open_file_with_editor` and `_main` in the module `flashcards.utils`. Alternatively you disable this button
TODO...


## Configuration
1. iterm2-enabled



Projection configurations must be set `MathNote/config.json` before the project
us usable. 
- `note-path`: full path to directory containing math notes. It is assumed that
   all `courses` reside in the directory `{note-path}/{course (e.g math-445)}`. 
   Furthermore lectures-- if created manually must reside in the directory
   `{note-path}/{course}/lectures/`. When using the CLI this is default
   behaviour.

- `main-template`: Full path to main file template. Main file refers to the file
  responsible for combining all lectures into one latex file. There is a default
  template in `MathNote/templates` (this is used by default), however other templates can be specified
- `macros-path`: Full path to macros.tex file, if relevant. This file specifies
  all user defined commands. 
- `macro-name`: List of all user defined commands in macros.tex, with backslashed excluded.
  For example suppose we have defined the command
  ```tex
    \newcommand{\norm}[1]{\left\lVert#1\right\rVert}
  ```
  Then we would have
  ```json
   "macro-names": ["norm",...] 
  ```

  Unfortunate there is no way to do this more dynamically at
  the moment.

- `section-names`: mapping between the section names and the shorthand versions used in tex files, 
    i.e [sectionName](#flashcard). For example one possible configuration would be
    ```json
    "section-names": {"DEFINITION": "defin", "THEOREM": "theo", "DERIVATION": "der",
    "PROOF": "pf", "COROLLARY": "corollary", "LEMMA": "lemma",
    "PROPOSITION": "proposition"},
    ```
    where `defin` is the section name used in the Tex file. Note that the sections in bold are the only available options, however
    it would not be very difficult to modify this behaviour yourself.

## Aknowledgment
This project was largely inspired by [https://castel.dev.post/lecture-notes-1](https://castel.dev/post/lecture-notes-1/), which I would 
highly recommend reading. If you are interested in typesetting your lecture notes in real time, you may find the following blog interesting 
[https://ejmastnak.com/tutorials/vim-latex/intro/](https://ejmastnak.com/tutorials/vim-latex/intro/)
