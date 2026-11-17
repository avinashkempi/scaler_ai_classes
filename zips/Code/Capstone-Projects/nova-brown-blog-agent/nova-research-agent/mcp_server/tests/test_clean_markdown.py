"""Tests for the LLM-based Markdown cleaning step used when scraping sources."""

import asyncio

from src.app.scraping_handler import clean_markdown


class _Reply:
    """Minimal stand-in for a LangChain AIMessage."""

    def __init__(self, content):
        """Store the reply content (a string or a list of content parts)."""
        self.content = content


class _FakeChatModel:
    """Chat model stub that returns a fixed reply."""

    def __init__(self, content):
        """Remember the content every call should return."""
        self._content = content

    async def ainvoke(self, prompt):
        """Return the canned reply, ignoring the prompt."""
        return _Reply(self._content)


def test_clean_markdown_joins_text_parts_only():
    """Gemini 3 style list replies keep only their text, never the raw part dicts or signatures."""
    parts = [
        {"type": "text", "text": "# Cleaned page\n\nUseful content.", "extras": {"signature": "abc123"}},
        {"type": "text", "text": "\nMore content."},
    ]
    result = asyncio.run(clean_markdown("# Raw page", "guidelines", "https://example.com", _FakeChatModel(parts)))

    assert result == "# Cleaned page\n\nUseful content.\nMore content."
    assert "signature" not in result and "{'type'" not in result


def test_clean_markdown_plain_string_reply():
    """Plain string replies are returned as-is."""
    result = asyncio.run(clean_markdown("# Raw page", "guidelines", "https://example.com", _FakeChatModel("# Clean")))

    assert result == "# Clean"
