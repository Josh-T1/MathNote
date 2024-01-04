from functools import partial
import logging


LEVEL = logging.DEBUG

logging.basicConfig(
        level=LEVEL,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        filename="shortcut_manager.log"
        )
logger = logging.getLogger(__name__)

class Descriptor:
    def __get__(self, instance, owner=None):
        return 5

class A:
    name = Descriptor()

    def __init__(self):
        self.patterns = {}

    def set_method(self, func):
        new_func = partial(func, A_instance=self)
        self.patterns['Test'] = new_func

def test():

    logger.info("this is a test")


def func(A_instance):
    print(A_instance.A)

def patterns(patterns):
    for i in patterns:
        pattern(*i)

def pattern(a, b, c, d=False):
    print(a)
    print(d)
if __name__ == '__main__':
#    p = [(1, 3, 4, True), (3, 4, 5, False)]
#    patterns(p)
    pattern(1, 2, 3,True)


