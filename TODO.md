
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
