import json
from flask import Flask, flash, render_template, jsonify
import sys
from course.parse_tex import def_flash_cards
from pathlib import Path
import re
import random

app = Flask(__name__)
# catch no flash cards error in app.js

#@app.route('/')
#def index():

#    return render_template('index.html', flashcards=flashcards[0])
#
#@app.route('/get_mathjax')
#def get_mathjax():
#    html_content = ""
#    return jsonify(content=html_content)
#

@app.route('/')
def index():
    return render_template('index.html')

path = Path("/Users/joshuataylor/documents/notes/uofc/math-445/lectures/lec_03.tex")
values = def_flash_cards(path)
flashcards = [{"question": val[1], "answer": val[0]} for val in values]
print(flashcards)

@app.route('/get_random_flashcard')
def get_random_flashcard():
    fl = random.choice(flashcards)
    return jsonify(fl)

def run():
    app.run(debug=True)

if __name__ == "__main__":
    app.run(debug=True)
