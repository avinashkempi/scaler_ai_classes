"""
ClaimSense — Agentic Motor Insurance Claims Processor
Author : Shivank Agrawal
File   : app/llm.py
Purpose: The ONLY file that talks to OpenAI. Every call returns (result, usage) so we can show
         the exact cost of processing each claim — a number every client asks for.

Three helpers:
  parse() -> structured output (a Pydantic object) using the Responses API
  write() -> free text (used for the customer letter)
  embed() -> embeddings for the policy-wording retrieval
"""

import base64
from functools import lru_cache
from pathlib import Path

import numpy as np
from openai import OpenAI
from pydantic import BaseModel

from app import config


@lru_cache
def client() -> OpenAI:
    """Created on first use, so modules can be imported even before OPENAI_API_KEY is set."""
    return OpenAI()  # reads OPENAI_API_KEY from the environment / .env


def _usage(step: str, model: str, input_tokens: int, output_tokens: int) -> dict:
    """Token counts -> cost in rupees, tagged with the graph step that spent it."""
    price_in, price_out = config.PRICES_USD_PER_1M.get(model, (0.0, 0.0))
    cost_usd = (input_tokens * price_in + output_tokens * price_out) / 1_000_000
    return {"step": step, "model": model, "input_tokens": input_tokens, "output_tokens": output_tokens,
            "cost_inr": round(cost_usd * config.USD_TO_INR, 4)}


def pdf_part(path: Path) -> dict:
    """Attach a PDF directly to the request. The model reads text AND layout (tables), so no OCR library needed."""
    data = base64.b64encode(path.read_bytes()).decode()
    return {"type": "input_file", "filename": path.name, "file_data": f"data:application/pdf;base64,{data}"}


def text_part(text: str) -> dict:
    return {"type": "input_text", "text": text}


def parse(step: str, instructions: str, content: list[dict], schema: type[BaseModel]) -> tuple[BaseModel, dict]:
    """
    Ask the model for an answer that MUST match `schema` (OpenAI structured outputs).
    temperature=0 -> same document gives (almost) the same extraction every time.
    """
    response = client().responses.parse(
        model=config.OPENAI_MODEL,
        instructions=instructions,
        input=[{"role": "user", "content": content}],
        text_format=schema,
        temperature=0,
    )
    usage = _usage(step, config.OPENAI_MODEL, response.usage.input_tokens, response.usage.output_tokens)
    return response.output_parsed, usage


def write(step: str, instructions: str, text: str) -> tuple[str, dict]:
    """Plain-text generation (customer letters)."""
    response = client().responses.create(
        model=config.OPENAI_MODEL,
        instructions=instructions,
        input=text,
        temperature=0.3,
    )
    usage = _usage(step, config.OPENAI_MODEL, response.usage.input_tokens, response.usage.output_tokens)
    return response.output_text.strip(), usage


def embed(step: str, texts: list[str]) -> tuple[np.ndarray, dict]:
    """Embed a list of texts. Returns an (n, d) numpy array of unit-length vectors."""
    response = client().embeddings.create(model=config.EMBEDDING_MODEL, input=texts)
    vectors = np.array([item.embedding for item in response.data], dtype=np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)  # unit length -> dot product = cosine similarity
    usage = _usage(step, config.EMBEDDING_MODEL, response.usage.prompt_tokens, 0)
    return vectors, usage
