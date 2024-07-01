# [General TODO]
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

1. ** Figure out Cache system
1. *** Add proof button and functionality/ Derivation

# === [Fix] ===
## ShortCutManager

1. Soft open... ie dont open new instance of inkscape but rather a new tab
1. Test new functionality allowed by using locks
1. Implement method for 'chaining shortcuts'
1. Close inkscape along with shortcut manager -- add a second 'soft close'
   shortcut to user_shortcuts

1. Figure out how to do saftey checks for user defined shortcuts
1. Send 'a' to buffer in fucntion write latex if possible
    - Can I distinguish between two vim instances?
1. Figure out add_latex shortcut 
    - The issue is I can not wait for the process to finish, so I can not
      implement paste
1. Fix focus()
1. Either open inkscape of use open instance??? How do I know if a file is begin
   used?? Figure out how to make it load faster
1. Extend dynamic loading of a file of shortcuts to dynamic loading of a folder
   or file
1. Currently you are unable to 'saftely' close shortcut_manager while a shortcut
   iis in progress. Look at comminicate_status. Consider threads checking
   self.mode to determine if they should terminate

## Course
1. Fix or verify that course start time feature works
1. Re think load_macros. Make dynamic so macros such as definition boxes can be
   converted to pure tex. Make Macro object that is returned by parse tex and
   used by remove tex.

## FlashCards


# === [New Features to Implement] ===
## Build Vector Graphics with PyQt5
1. This is a mission

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

# GUI

# === [Snippets] ===
1. Figure out a better system for creating snippets, can I make a script to
   check and see if snippets 'collide'
1. Consider keymaps that send buffer contents to script
1. Dynamical generate use lists


