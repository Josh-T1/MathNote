from ..course.parse_tex import  FlashcardsPipeline, TexDataGenerator, CleanStage, FilterBySectionAndMakeFlashcardsStage, TrackedString
from pathlib import Path
from .flashcard_model import TexCompilationManager, FlashcardModel



#def test():
#    text = ""
#    pattern = rf'^\\(defin){{(.*?)}}'
#    re.match(pattern, text)


#def test_macro():
#    path = Path(__file__).parent / "test.tex"
#    model = FlashcardModel(TexCompilationManager())
#    macros = model._load_macros()
#    tex = path.read_text('utf-8')
#    tex = TrackedString(tex, source_history=None)
#    clean = CleanStage(macros)
#    tex = clean.remove_macros(tex)
#    print(tex)


if __name__ == '__main__':
    path = Path("/Users/joshuataylor/documents/notes/uofc/math-445/lectures/lec_03.tex")
#
    model = FlashcardModel(TexCompilationManager())
    macros = model._load_macros()
#    print(macros)
    data = TexDataGenerator([path])
    clean = CleanStage(macros)
    flashcards_builder = FilterBySectionAndMakeFlashcardsStage(['defin'])
    pipe = FlashcardsPipeline(data, flashcards_builder ,stages = [clean])
    for chunk in pipe:
        print(chunk)
#
