"""Media items (e.g. Mermaid diagrams) generated for an article."""

from abc import ABC

from pydantic import BaseModel

from brown.entities.mixins import ContextMixin


class MediaItem(BaseModel, ContextMixin, ABC):
    """Base class for a generated media item and the place it goes in the article."""

    location: str
    content: str
    caption: str

    def to_context(self) -> str:
        """Wrap the media item in XML tags for an LLM prompt."""
        return f"""
<{self.xml_tag}>
    <location>{self.location}</location>
    <content>{self.content}</content>
    <caption>{self.caption}</caption>
</{self.xml_tag}>
"""


class MediaItems(BaseModel, ContextMixin):
    """A collection of generated media items."""

    media_items: list[MediaItem] | None

    @classmethod
    def build(cls, media_items: list[MediaItem] | None = None) -> "MediaItems":
        """Create the collection. ``None`` means the media items already live in the source article."""
        return cls(media_items=media_items)

    @property
    def are_available_only_in_source(self) -> bool:
        """True when nothing was generated and the writer should keep the media items already in the article."""
        return self.media_items is None

    def to_context(self) -> str:
        """Wrap all media items in XML tags for an LLM prompt."""
        if self.are_available_only_in_source:
            media_items_context = "media items are available only in the source file"
        else:
            media_items_context = "\n".join([media_item.to_context() for media_item in self.media_items])

        return f"""
<{self.xml_tag}>
{media_items_context}
</{self.xml_tag}>
"""


class MermaidDiagram(MediaItem):
    """A Mermaid diagram generated from a text description."""

    pass
