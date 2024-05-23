from utils import write_latex, open_vim
from filelock import FileLock
from config import PIPELINE_FILENAME, LOCK_FILENAME
import time



if __name__ == '__main__':
    lock = FileLock(LOCK_FILENAME)
    lock.acquire()
    try:
        write_latex()
    finally:
        with open(PIPELINE_FILENAME, "w") as file:
            file.write("done")
        lock.release()

