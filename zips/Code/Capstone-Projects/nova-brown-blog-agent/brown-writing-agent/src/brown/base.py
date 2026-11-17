"""Abstract base classes for loading inputs and rendering outputs."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class Loader(ABC):
    """Base class for anything that loads an input (guideline, research, profiles, ...) from a URI."""

    def __init__(self, uri: Any) -> None:
        """Store the URI (file path, directory or mapping) the loader reads from."""
        self.uri = uri

    @abstractmethod
    def load(self, working_uri: Any | None = None, *args, **kwargs) -> Any:
        """Load the input and return it as a domain entity.

        Args:
            working_uri: Optional base location (e.g. the article directory) the URI is resolved against.

        Returns:
            The loaded entity.
        """
        pass


class Renderer(ABC):
    """Base class for anything that writes an output (e.g. the final article) to disk."""

    @abstractmethod
    def render(self, content: Any, *, output_uri: Path) -> None:
        """Write ``content`` to ``output_uri``."""
        pass
