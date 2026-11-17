"""Application config loaded from a YAML file in ``configs/`` (models, review loop, input/output paths)."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from annotated_types import Ge
from pydantic import BaseModel, DirectoryPath, Field, field_validator

from brown.config import get_settings
from brown.models.config import ModelConfig, SupportedModels


class Context(BaseModel):
    """Where Brown reads its inputs from and writes its outputs to, and which loader/renderer to use."""

    article_guideline_loader: Literal["markdown"]
    article_guideline_uri: Path = Field(description="URI to the article guideline file.")

    research_loader: Literal["markdown"]
    research_uri: Path = Field(description="URI to the research file.")

    article_loader: Literal["markdown"]
    article_renderer: Literal["markdown"]
    article_uri: Path = Field(description="URI to the article file.")

    profiles_loader: Literal["markdown"]
    profiles_uri: Annotated[DirectoryPath, Field(description="URI to the profiles directory.")]
    character_profile: str

    examples_loader: Literal["markdown"]
    examples_uri: Annotated[DirectoryPath, Field(description="URI to the examples directory.")]

    def build_article_uri(self, iteration: int) -> Path:
        """Return the checkpoint path for a review iteration, e.g. ``article.md`` -> ``article_001.md``."""
        return self.article_uri.with_stem(f"{self.article_uri.stem}_{iteration:03d}")


class Memory(BaseModel):
    """Which LangGraph checkpointer stores workflow state (in memory or SQLite)."""

    checkpointer: Literal["in_memory", "sqlite"]


class ToolConfig(BaseModel):
    """Model settings for a tool used by a node (e.g. the Mermaid diagram generator)."""

    name: str
    model_id: SupportedModels
    config: ModelConfig


class NodeConfig(BaseModel):
    """Model settings for one workflow node, plus the tools it can call."""

    model_id: SupportedModels
    config: ModelConfig
    tools: dict[str, ToolConfig]


class AppConfig(BaseModel):
    """Top-level app config: context paths, memory, review-loop limits and per-node model settings."""

    context: Context
    memory: Memory

    num_reviews: Annotated[int, Ge(1), Field(description="The number of reviews to perform while generating the article the first time.")]
    max_reviews_per_iteration: Annotated[
        int,
        Ge(1),
        Field(default=5, description="Maximum reviews the article reviewer may emit per call (caps the editor's context window)."),
    ]
    nodes: dict[str, NodeConfig]

    @field_validator("nodes", mode="before")
    @classmethod
    def parse_nodes(cls, v: Any) -> dict[str, NodeConfig]:
        """Parse nodes configuration from YAML data."""
        if isinstance(v, dict):
            result = {}
            for node_name, node_config in v.items():
                # Convert model_id string to SupportedModels enum
                model_id_str = node_config.get("model_id", "")
                try:
                    model_id = SupportedModels(model_id_str)
                except ValueError:
                    raise ValueError(f"Invalid model_id '{model_id_str}'. Must be one of: {', '.join([m.value for m in SupportedModels])}")

                # Create ModelConfig from the model_config dict
                model_config_dict = node_config.get("model_config", {})
                model_config = ModelConfig(**model_config_dict)

                # Parse tools if they exist
                tools = {}
                if "tools" in node_config:
                    for tool_name, tool_config in node_config["tools"].items():
                        tool_model_id_str = tool_config.get("model_id", "")
                        try:
                            tool_model_id = SupportedModels(tool_model_id_str)
                        except ValueError:
                            raise ValueError(
                                f"Invalid tool model_id '{tool_model_id_str}'. Must be one of: {', '.join([m.value for m in SupportedModels])}"  # noqa: E501
                            )

                        tool_config_dict = tool_config.get("config", {})
                        tool_model_config = ModelConfig(**tool_config_dict)

                        tools[tool_name] = ToolConfig(name=tool_name, model_id=tool_model_id, config=tool_model_config)

                result[node_name] = NodeConfig(model_id=model_id, config=model_config, tools=tools)
            return result
        return v

    @classmethod
    def from_yaml(cls, file_path: Path) -> "AppConfig":
        """Load configuration from a YAML file."""

        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls(**data)


@lru_cache(maxsize=1)
def get_app_config() -> AppConfig:
    """Load the YAML config pointed to by ``CONFIG_FILE`` once and cache it."""
    return AppConfig.from_yaml(get_settings().CONFIG_FILE)
