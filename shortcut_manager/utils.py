import subprocess
import sys
sys.path.insert(0, '../')
import os
#config = Config()['inkscape-config']
#def open_inkscape(path: str):
#    subprocess.Popen([config['inkscape'], path])

def clear_tmp_dir(path:str):
    with open(path, mode='r') as f:
        files = f.read().split('\n') # how do i do this?
#    for file in files:
#        os.remove()

def focus(app_name):
    cmd = f'osascript -e \'activate application "{app_name}"\''
    subprocess.call(cmd, shell=True) # unsafe?


