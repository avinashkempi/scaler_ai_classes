"""Article entities: the article itself, a selected slice of it, and example articles."""

from pydantic import BaseModel

from brown.entities.mixins import ContextMixin, MarkdownMixin


class Article(BaseModel, ContextMixin, MarkdownMixin):
    """A full article in Markdown."""

    content: str

    def to_context(self) -> str:
        """Wrap the article in XML tags so it can be dropped into an LLM prompt."""
        return f"""
<{self.xml_tag}>
    {self.content}
</{self.xml_tag}>
"""

    def to_markdown(self) -> str:
        """Return the raw Markdown content."""
        return self.content

    def __str__(self) -> str:
        """Short summary used in logs."""
        return f"Article(len_content={len(self.content)})"


class SelectedText(BaseModel, ContextMixin):
    """A slice of an article (by line numbers) that the user wants to edit."""

    article: Article
    content: str
    first_line_number: int
    last_line_number: int

    def to_context(self, include_article: bool = False) -> str:
        """Wrap the selection in XML tags for an LLM prompt.

        Args:
            include_article: Also include the full article for context.
        """
        return f"""
<{self.xml_tag}>
    {f"<article>{self.article.to_context()}</article>" if include_article else ""}
    <content>{self.content}</content>
    <first_line_number>{self.first_line_number}</first_line_number>
    <last_line_number>{self.last_line_number}</last_line_number>
</{self.xml_tag}>
"""


class ArticleExample(BaseModel, ContextMixin):
    """An example article used as a style reference."""

    content: str

    def to_context(self) -> str:
        """Wrap the example in XML tags for an LLM prompt."""
        return f"""
<{self.xml_tag}>
    {self.content}
</{self.xml_tag}>
"""

    def __str__(self) -> str:
        """Short summary used in logs."""
        return f"ArticleExample(len_content={len(self.content)})"


class ArticleExamples(BaseModel, ContextMixin):
    """A collection of example articles."""

    examples: list[ArticleExample]

    def to_context(self) -> str:
        """Wrap all examples in XML tags for an LLM prompt."""
        return f"""
<{self.xml_tag}>
        {"\n".join([example.to_context() for example in self.examples])}
</{self.xml_tag}>
"""
