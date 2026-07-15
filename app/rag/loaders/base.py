from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LoadedPage:
    text: str
    page_number: int
    metadata: dict = field(default_factory=dict)


class BaseLoader(ABC):
    @abstractmethod
    def load(self, file_path: str) -> list[LoadedPage]:
        """Load a file and return its content as a list of LoadedPage objects."""
        pass
