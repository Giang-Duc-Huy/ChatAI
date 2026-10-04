from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

logger = logging.getLogger(__name__)


@dataclass
class StageTimer:
    stages: dict[str, float] = field(default_factory=dict)
    _starts: dict[str, float] = field(default_factory=dict)

    def start(self, name: str) -> None:
        self._starts[name] = time.perf_counter()

    def stop(self, name: str) -> float:
        started = self._starts.pop(name, None)
        if started is None:
            return 0.0
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        self.stages[name] = round(elapsed_ms, 2)
        return self.stages[name]

    @contextmanager
    def measure(self, name: str) -> Iterator[None]:
        self.start(name)
        try:
            yield
        finally:
            self.stop(name)

    def as_dict(self) -> dict[str, float]:
        return dict(self.stages)

    def log(self, prefix: str = "timings") -> None:
        logger.info("%s %s", prefix, self.stages)


def now_ms() -> float:
    return time.perf_counter() * 1000.0
