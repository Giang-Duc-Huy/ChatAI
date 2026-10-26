import json, time
from contextlib import contextmanager
from .config import LOG_FILE

class Timer:
    def __init__(self):
        self.ms = {}
        self._t0 = time.perf_counter()

    @contextmanager
    def stage(self, name):
        t = time.perf_counter()
        try:
            yield
        finally:
            self.ms[name] = round((time.perf_counter() - t) * 1000, 1)

    def total(self):
        self.ms["total"] = round((time.perf_counter() - self._t0) * 1000, 1)
        return self.ms

def log(entry: dict):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **entry}
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
