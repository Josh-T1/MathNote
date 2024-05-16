
# Issues
1. DONT allow files with no name to be created, inscape svg problem

1. Allow for course detection based on existance of course_info.json
1. Make misc folder and include in main.tex at end
1. make 1x1 vectors
1. 

1. organize snippets - create snippet rules





# shortcut manager 
-- resposabilies --
1. Manage shortcuts
1. Use vim to edit latex images

todo
1. Figure out how to send cmd-v
1. How can i capture multi char shortcuts
1. focus iterm2 window
1. start from vim
1. add code to vim to include figure??? or should this be done by figure manager
1. Save and close shourtcut -> on save converts to latex and moves to proper
   directory


# Inkscape_vim
-- resposabilies --
1. Add code to latex file
1. Open figure in inkscape 
1. Edit figure in inkscape when figure already exits

todo
1. Open and Close figures in inkscape 
1. call shortucut manager when launching
    - run()








inkscape-figures -> runs in backgroud

# In vim use ctrl on the line with figure title
this does:

1. find dir where figures should be stored using b:vimtex.root -> gives path
2. Check if there exists a figure with the same name
3. Copy the figure template to the directory containg figure
4. in vim add corresponding figure code
5. open figure in inkscape
6. Set u pa file whatcher that makes sure all saved figures are saved also saved
   as pdf+latex

i) Use ctrl F in command mode and a fuzzy search selection for figures appears
    - is this in inkscape of vim?
    - probably inkscape

# DON
1. Create Manager() obj before inkscape is started
vim mapping 1 -> starts


# My Way
SCRIPT 1
1. start inkscpae
    i. send script to start inkscape relevent path

2. start hotkey manager -> some sort of while loop while its running
3. Once inkscape terminates then deal with the saving automation

SCRIPT 2
- Method for quickly editing figure
- Implement fuzzy find
/Applications/inkscape.app/contents/macos/./inkscape --export-type="png" --export-dpi=300 testfile.svg
osascript -e 'set the clipboard to (read (POSIX file /Users/joshuataylor/Desktop/test.jpeg) as JPEG picture)'
osascript -e 'set the clipboard to (read (POSIX file /Users/joshuataylor/Desktop/tmp97mpl_3z.png) as  {«class PNGf»})'
/var/folders/22/jdx_plts6rvcy7w4dx7z3lzm0000gn/T/tmpmdqzltyi.png



[[ Latex ]]
* how do i change imports to no longer be relative
* script to remove inclusively everthing above and below begin/end{document}
* Have these files be moved into a new directory
    - Make a debug script, clearns out all non .tex files upon start up (maybe even tex file)
    - moves into debug folder where its compiled, command to end debug (delete files)

[[ Script ]]

* Why is a file being named figure name


* Can i use fzf and dear pygui to replicate choose
* if i create a figure then later decide to remove it from latex code -> how can i remove correspoinding pdf and pdf_latex files
figure out why pygui window does not close even though it receives message
how long does it take for everthing to load

tomorrow
1. figure out how to organize config
1. get latex figures out
1. automate creating latex files courses ect with user input
1. figure out a debug mode for latex files
1. make function to include latex code in main file

1. figure out what other inkscape shortcuts are required





