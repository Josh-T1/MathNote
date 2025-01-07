# MathNote
![flashcard](assets/flashcard.png)

This package aims to streamline the latex note taking process. This command line interface has three main commands:


1. `course`: command used for setting up the directory structure and other housekeeping tasks
2. `flashcard`: used to generate pdf flashcards, parsed from tex files
3. `note`: used for creating and managing short notes.


## Flashcard
The `flashcard` command requires lecture notes to follow fairly strict formatting. In order to generate flashcards
from a tex file, all relevant definitions, theorems, and other sections, must be contained in their own
"namespace", having the syntax
```
\{sectionName}{ ... }{
latex code
}
```
where sectionName would be one of: "definitions, "theorem", "proof", ect.
Additionally theorem/lemma/proposition flashcards by default include the proof as an additional "answer". Note that theorem/lemma/proposition
sections flashcards will only have a corresponding proof when directly followed by a proof section in the tex file.
For example:
```
\theo{Pythagorean theorem}{
pythagonrean theorem statement
}
\pf{}{
pythagorean theorem proof
}
```
Any Tex file following the above syntactic rules will allow for the generation of flashcards-- my personal
approach has been to define a `newtcbtheorem` environment for each section. All sections must be specified in the
configuration file, for more details look [configuration](#configuration)

## Course



## Note




## Configuration
Any directory under under the `note-path` (see config.json setup section) with a 
`course_info.json` file will be detected as course.


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
- `macro-name`: List of names all commands defined in macros.tex where each name
  excluded backslash. Unfortunate there is no way to do this more dynamically at
  the moment. An example of this would be the command: 

- `section-names`: mapping between the section names and the shorthand versions used in tex files, 
    i.e [sectionName](#flashcard). For example one possible configuration would be
    ```json
    "section-names": {"DEFINITION": "defin", "THEOREM": "theo", "DERIVATION": "der",
    "PROOF": "pf", "COROLLARY": "corollary", "LEMMA": "lemma",
    "PROPOSITION": "proposition"},
    ```
    where `defin` is the section name used in the Tex file. Note that the sections in bold are the only supported 
    sections, however by modifying the combo box options in the module gui/window, you may include the sections
    of your choosing.
