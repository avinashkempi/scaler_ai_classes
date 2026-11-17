"""Model-related exceptions."""

from brown.entities.exceptions import BrownException


class UnsupportedModelError(BrownException):
    """Raised when an unsupported model is used."""

    def __init__(self, model: str) -> None:
        """Create the exception for an unsupported model name."""
        super().__init__(f"Unsupported model: {model}")
