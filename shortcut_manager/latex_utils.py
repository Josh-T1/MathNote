from utils import write_latex
from filelock import FileLock
from config import PIPELINE_FILENAME, LOCK_FILENAME

lock = FileLock(LOCK_FILENAME)

if __name__ == '__main__':
    try:
       write_latex()
    finally:
        lock.acquire()
        with open(PIPELINE_FILENAME, "w") as file:
            file.write("done")

