"""Article guideline entities: what the user wants the article to contain."""

from pydantic import BaseModel

from .mixins import ContextMixin


class SectionGuideline(BaseModel, ContextMixin):
    """The guideline for a single section of the article."""

    title: str
    content: str

    def to_context(self) -> str:
        """Wrap the section guideline in XML tags for an LLM prompt."""
        return f"""
<{self.xml_tag}>
    <title>{self.title}</title>
    <content>{self.content}</content>
</{self.xml_tag}>
        """

    def __str__(self) -> str:
        """Short summary used in logs."""
        return f"SectionGuideline(title={self.title}, len_content={len(self.content)})"


class ArticleGuideline(BaseModel, ContextMixin):
    """The full article guideline (outline, audience, requirements) written by the user."""

    content: str

    def to_context(self) -> str:
        """Wrap the guideline in XML tags for an LLM prompt."""
        return f"""
<{self.xml_tag}>
    <content>{self.content}</content>
</{self.xml_tag}>
"""

    def __str__(self) -> str:
        """Short summary used in logs."""
        return f"ArticleGuideline(len_content={len(self.content)})"
