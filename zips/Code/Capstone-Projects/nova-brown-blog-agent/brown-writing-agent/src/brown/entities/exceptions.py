"""Exceptions raised by Brown."""

from pathlib import Path


class BrownException(Exception):
    """Base exception for Brown."""


class InputNotFoundException(BrownException):
    """Exception raised when the input is not found."""

    def __init__(self, input_path: Path) -> None:
        """Create the exception for a missing input path."""
        self.input_path = input_path

        super().__init__(f"Input source not found: `{self.input_path}`")


class InvalidOutputTypeException(BrownException):
    """Exception raised when the output type is invalid."""

    def __init__(self, expected_type: type, output_type: type) -> None:
        """Create the exception from the expected and actual output types."""
        self.expected_type = expected_type
        self.output_type = output_type

        super().__init__(f"Invalid output type. Expected `{self.expected_type}`, got `{self.output_type}`")


class InvalidConfigurationException(BrownException):
    """Exception raised when the configuration is invalid."""

    def __init__(self, message: str) -> None:
        """Create the exception with a description of what is misconfigured."""
        self.message = message

        super().__init__(f"Invalid configuration: `{self.message}`")
