"""Brown: the writing agent that turns an article guideline and research into a finished article.

Importing the package loads the settings and, when ``OPIK_ENABLED`` is true, configures Opik tracing.
"""

from brown import config, observability

__all__ = ["config"]

if config.get_settings().OPIK_ENABLED:
    observability.configure()
