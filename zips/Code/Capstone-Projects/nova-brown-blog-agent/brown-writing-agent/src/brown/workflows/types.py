"""Shared types for the workflows."""

from typing import Annotated

from annotated_types import Ge, Le
from pydantic import BaseModel


class WorkflowProgress(BaseModel):
    """A progress update streamed to the client while a workflow runs (0-100% plus a message)."""

    progress: Annotated[int, Ge(0), Le(100)]
    message: str
