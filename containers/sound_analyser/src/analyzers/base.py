from abc import ABC, abstractmethod
from typing import Any


class BaseAnalyzer(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def analyze(self, filepath: str) -> dict[str, Any]:
        """Process a file and return a dictionary of results.
        Raises exceptions on failure.
        """
        pass
