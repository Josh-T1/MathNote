# [General TODO]
1. Make tests dir under MathNote
1. Write tests
1. Write documentation
1. Consider making shortcut manager its own package (inkscape shortcut manager)
1. Ensure all functions have param type hinting and docstrings
    - Is it worth writing a guide for every function implemented
    - At minimum some files should have doc string to explain what is happening
      (parse_tex begin one)
1. Sort out CLI
    - Should there be one main CLI?
    - Rename project to Notes?
1. Allow for variable operating systems
1. Figure out how to make this a package?

# [Fix]
## ShortCutManager
1. DON'T allow files with no name to be created, inscape svg problem
1. Make sure focus works for inkscape
1. Either open inkscape of use open instance??? How do I know if a file is begin
   used?? Figure out how to make it load faster

## Course
1. Fix or verify that course start time feature works

## FlashCards



# [New Features to Implement]
## Flash Cards
1. Make formatting nice
1. Figure out how to get theorem proof flash cards
    - Take into account there may be several proof boxes
    - Default to first box

## ShortCutManager
1. Load user shortcuts from a directory
1. WHAT TO DO about problems from textbooks
1. Allow for course detection based on existance of course_info.json
1. Make misc folder and include in main.tex at end

1. Implement fuzzy search for figures
    Use ctrl F in command mode and a fuzzy search selection for figures appears
        - is this in inkscape of vim?
        - probably inkscape



# [Snippets]
1. Figure out a better system for creating snippets, can I make a script to
   check and see if snippets 'collide'



