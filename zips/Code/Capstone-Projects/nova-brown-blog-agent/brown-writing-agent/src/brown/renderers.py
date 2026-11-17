"""Renderers that write Brown's outputs to disk."""

from pathlib import Path

from brown.base import Renderer
from brown.entities.articles import Article
from brown.entities.reviews import ArticleReviews


class MarkdownArticleRenderer(Renderer):
    """Write an article to a Markdown file."""

    def render(self, content: Article, *, output_uri: Path) -> None:
        """Write the article to ``output_uri``, replacing any existing file."""
        if output_uri.exists():
            output_uri.unlink()
        output_uri.write_text(content.to_markdown())


class MarkdownArticleReviewsRenderer(Renderer):
    """Write article reviews to a Markdown file."""

    def render(self, content: ArticleReviews, *, output_uri: Path) -> None:
        """Write the reviews to ``output_uri``, replacing any existing file."""
        if output_uri.exists():
            output_uri.unlink()
        output_uri.write_text(content.to_context(include_article=False))
