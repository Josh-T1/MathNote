from pathlib import Path
import json
import threading
import logging


logger = logging.getLogger(__name__)


def load_json(file: str):
    with open(file, "r") as f:
        contents = json.load(f)
    return contents


def dump_json(file: str, contents: str) -> None:
    with open(file, "w") as f:
        json.dump(contents, f)


def rendered_sorted_key(path: Path) -> int:
    num = int(path.name.split(".")[0].split("-")[1])
    return num


class StoppableThread(threading.Thread):
    """
    Accepts kwarg 'callback' of type Callable that is called by StoppableThread._run() on every loop for which the _stop_event
    is not set. The callback must accept one parameter: threading.Event(). If the callback implements its own blocking behaviour it must
    break out of that state when even it set (see FlashcardModel.compile)
    """
    def __init__(self, *args, **kwargs):
        self._stop_event = threading.Event()
        self._stopped_properly = threading.Event()
        self.inner_target = kwargs.get("callback")
        del kwargs["callback"]
        kwargs["target"] = self._run
        super().__init__(*args, **kwargs)

    def stopped(self) -> bool:
        return self._stop_event.is_set()

    def _run(self):
        logger.debug(f"Starting {self.__class__.__name__}")
        while not self.stopped():
            if self.inner_target:
                self.inner_target(self._stop_event)
        self._stopped_properly.set()

    def wait_for_stop(self):
        """ waits for stop event and resets events """
        logger.debug(f"{self.__class__.__name__} waiting for stop")
        self._stopped_properly.wait()

    def reset_events(self):
        logger.debug(f"reseting {self.__class__.__name__} events")
        self._stop_event.clear()
        self._stopped_properly.clear()

    def stop(self):
        logger.debug(f"Setting {self.__class__.__name__} stop event")
        self._stop_event.set()

