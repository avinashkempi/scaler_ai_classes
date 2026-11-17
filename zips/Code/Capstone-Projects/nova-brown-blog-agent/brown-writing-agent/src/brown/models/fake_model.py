"""A fake chat model that returns canned responses, so tests run without API calls."""

import json
from typing import Any, Self, Type

from langchain_community.chat_models import FakeListChatModel
from loguru import logger


class FakeModel(FakeListChatModel):
    """Fake chat model that replays fixed responses and supports structured output and tool binding."""

    def __init__(self, responses: list[str]) -> None:
        """Create the fake model with the responses it should return."""
        super().__init__(responses=responses)

        self._structured_output_type: Type[Any] | None = None
        self._include_raw: bool = False

    def bind_tools(self, tools, *args, **kwargs) -> Self:
        """Accept tools but ignore them (the fake model never calls tools)."""
        return self

    def with_structured_output(self, output_type: Type[Any], include_raw: bool = False) -> Self:
        """Remember the output type so ``ainvoke`` can parse the canned response into it."""
        self._structured_output_type = output_type
        self._include_raw = include_raw

        return self

    async def ainvoke(self, inputs, *args, **kwargs) -> Any:
        """Return the canned response, parsed into the structured output type when one is set."""
        if len(self.responses) == 0:
            return []

        if self._structured_output_type is not None:
            # For structured output, we need to handle the mocked response directly
            # without going through the parent's ainvoke method which creates AIMessage
            response_content = self.responses[0]

            if isinstance(response_content, dict):
                structured_response = self._structured_output_type(**response_content)
            elif isinstance(response_content, str):
                try:
                    data = json.loads(response_content)
                    structured_response = self._structured_output_type(**data)
                except Exception:
                    logger.warning(f"Failed to parse response as JSON: {response_content}")
                    raise ValueError(f"Failed to parse response as JSON: {response_content}")
            else:
                raise NotImplementedError(f"Unsupported response type: {type(response_content)}")

            if self._include_raw:
                # For raw output, we still need to create a proper AIMessage
                from langchain_core.messages import AIMessage

                raw_message = AIMessage(content=response_content)
                return {
                    "parsed": structured_response,
                    "raw": raw_message,
                }
            else:
                return structured_response

        # For non-structured output, use the parent's implementation
        response = await super().ainvoke(inputs, *args, **kwargs)
        return response
