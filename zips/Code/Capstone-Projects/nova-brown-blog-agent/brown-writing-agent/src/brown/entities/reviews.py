"""Review entities: reviewer comments and human feedback used to edit articles."""

from pydantic import BaseModel, Field

from brown.entities.articles import Article, SelectedText
from brown.entities.mixins import ContextMixin


# One reviewer comment: which profile rule is broken, where in the article, and what is wrong.
# (Comment instead of a docstring: this model is sent to the LLM as the structured-output schema.)
class Review(BaseModel, ContextMixin):
    profile: str = Field(description="The profile type listing the constraints based on which we will write the comment.")
    location: str = Field(
        description="The location from within the article where the comment is made. For example, the title of a section."
    )
    comment: str = Field(description="The comment made by the reviewer stating the issue relative to the profile.")

    def to_context(self) -> str:
        """Wrap the review in XML tags for an LLM prompt."""
        return f"""
<{self.xml_tag}>
    <profile>{self.profile}</profile>
    <location>{self.location}</location>
    <comment>{self.comment}</comment>
</{self.xml_tag}>
"""


class ArticleReviews(BaseModel, ContextMixin):
    """All reviews generated for a full article."""

    article: Article
    reviews: list[Review]

    def to_context(self, include_article: bool = False) -> str:
        """Wrap the reviews in XML tags for an LLM prompt.

        Args:
            include_article: Also include the reviewed article.
        """
        reviews_str = "\n".join([review.to_context() for review in self.reviews])
        return f"""
<{self.xml_tag}>
    {f"<article>{self.article}</article>" if include_article else ""}
    <reviews>
    {reviews_str}
    </reviews>
</{self.xml_tag}>
"""

    def __str__(self) -> str:
        """Short summary used in logs."""
        return f"Reviews(len_reviews={len(self.reviews)})"


class SelectedTextReviews(BaseModel, ContextMixin):
    """All reviews generated for a selected piece of text."""

    article: Article
    selected_text: SelectedText
    reviews: list[Review]

    def to_context(self, include_article: bool = False) -> str:
        """Wrap the reviews and the selected text in XML tags for an LLM prompt.

        Args:
            include_article: Also include the full article.
        """
        reviews_str = "\n".join([review.to_context() for review in self.reviews])
        return f"""
<{self.xml_tag}>
    {f"<article>{self.article.to_context()}</article>" if include_article else ""}
    <selected_text>{self.selected_text.to_context()}</selected_text>
    <reviews>
    {reviews_str}
    </reviews>
</{self.xml_tag}>
"""


class HumanFeedback(BaseModel, ContextMixin):
    """Free-text feedback from the user that guides an edit."""

    content: str

    def to_context(self) -> str:
        """Wrap the feedback in XML tags for an LLM prompt."""
        return f"""
<{self.xml_tag}>
    {self.content}
</{self.xml_tag}>
"""
