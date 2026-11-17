"""Writing profiles: reusable rules that shape how every article is written."""

from pydantic import BaseModel

from brown.entities.mixins import ContextMixin


class Profile(BaseModel, ContextMixin):
    """Base writing profile: a named block of Markdown rules."""

    name: str
    content: str

    def to_context(self) -> str:
        """Wrap the profile in XML tags for an LLM prompt."""
        return f"""
<{self.xml_tag}>
    <name>{self.name}</name>
    <content>{self.content}</content>
</{self.xml_tag}>
"""


class CharacterProfile(Profile):
    """The author persona the writer impersonates (voice, background, niche)."""

    pass


class ArticleProfile(Profile):
    """Rules specific to writing articles."""

    pass


class StructureProfile(Profile):
    """Rules for the structure and formatting of the output."""

    pass


class MechanicsProfile(Profile):
    """Rules for sentence- and paragraph-level writing mechanics."""

    pass


class TerminologyProfile(Profile):
    """Rules for word choice and phrasing."""

    pass


class TonalityProfile(Profile):
    """Rules for tone and voice."""

    pass


class ArticleProfiles(BaseModel):
    """All profiles needed to write or review an article."""

    character: CharacterProfile

    article: ArticleProfile

    structure: StructureProfile
    mechanics: MechanicsProfile
    terminology: TerminologyProfile
    tonality: TonalityProfile
