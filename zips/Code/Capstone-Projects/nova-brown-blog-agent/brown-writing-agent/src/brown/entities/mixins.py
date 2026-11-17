"""Mixins that give entities a prompt (XML) or Markdown representation."""

from abc import abstractmethod

from brown.utils.s import camel_to_snake


class ContextMixin:
    """Adds ``to_context()`` so an entity can be placed inside an LLM prompt."""

    @property
    def xml_tag(self) -> str:
        """XML tag name derived from the class name (``ArticleGuideline`` -> ``article_guideline``)."""
        return camel_to_snake(self.__class__.__name__)

    @abstractmethod
    def to_context(self) -> str:
        """Context representation of the object."""

        pass


class MarkdownMixin:
    """Adds ``to_markdown()`` so an entity can be saved as Markdown."""

    @abstractmethod
    def to_markdown(self) -> str:
        """Markdown representation of the object."""

        pass
