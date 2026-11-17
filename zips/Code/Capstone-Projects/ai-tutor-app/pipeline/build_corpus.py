"""
Step 2 of the data pipeline: clean the markdown and cut it into chunks.

Author: Shivank Agrawal
Project: AI Tutor (Agentic RAG) - Future with Shivank

Input : data/docs/<source>/**/*.md   (from step 1)
Output: data/documents.jsonl  - one cleaned page per line (used by step 3, the KB)
        data/chunks.jsonl     - search-sized pieces of each page (used by step 4
                                and by the keyword search at runtime)

Chunking is "heading-aware": we split a page at its markdown headings first,
never inside a ``` code block, then pack neighbouring sections together until
a chunk reaches ~CHUNK_TOKENS. Every chunk remembers its heading path
(e.g. "LoRA > Initialization"), which we prepend before embedding so a small
chunk still carries the context of where it came from.

Run from the project root:
    python -m pipeline.build_corpus
"""

import json
import re
from pathlib import Path

from app.config import CHUNK_TOKENS, CHUNKS_FILE, DOCS_DIR, DOCUMENTS_FILE, SOURCES

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
# Lines that are only a JSX/HTML tag (<Tip>, </hfoption>, ...), a HF doc-builder
# directive ([[autodoc]] ...), or an mkdocs API directive (::: agents.Agent).
NOISE_LINE_RE = re.compile(r"^\s*(</?[A-Za-z][^>]*>|\[\[.*\]\]|:::\s.*)\s*$")


def count_tokens(text: str) -> int:
    """Rough token count: ~4 characters per token for English text and code."""
    return len(text) // 4 + 1


# ---------------------------------------------------------------------------
# Cleaning and metadata
# ---------------------------------------------------------------------------
def clean_markdown(text: str) -> str:
    """Remove licence headers, doc-builder tags and extra blank lines."""
    text = HTML_COMMENT_RE.sub("", text)
    lines = [line for line in text.splitlines() if not NOISE_LINE_RE.match(line)]
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def page_title(text: str, path: Path) -> str:
    """First '# Heading' of the page, otherwise a title made from the file name."""
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match and len(match.group(1)) == 1:
            return match.group(2).strip()
    return path.stem.replace("_", " ").replace("-", " ").title()


def page_url(key: str, relative: str) -> str:
    """Public URL of the page, so the tutor can cite the real documentation."""
    base = SOURCES[key]["url_base"]
    slug = re.sub(r"\.mdx?$", "", relative)
    if key == "openai_agents":  # mkdocs site: folder-style URLs ending in '/'
        slug = re.sub(r"(^|/)index$", "", slug)
        return base + (slug + "/" if slug else "")
    if slug == "index":  # Hugging Face doc-builder site
        return base
    return base + slug


# ---------------------------------------------------------------------------
# Heading-aware chunking
# ---------------------------------------------------------------------------
def split_into_sections(text: str) -> list[tuple[str, str]]:
    """Cut a page at its headings -> [(heading_path, section_text), ...].

    Lines inside ``` code fences are never treated as headings, because a
    '# comment' in Python code is not a markdown heading.
    """
    sections: list[tuple[str, str]] = []
    path: list[str] = []
    buffer: list[str] = []
    in_code = False

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if body:
            sections.append((" > ".join(path), body))

    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
        match = None if in_code else HEADING_RE.match(line)
        if match:
            flush()
            buffer = []
            level = len(match.group(1))
            path = path[: level - 1] + [match.group(2).strip()]
        buffer.append(line)
    flush()
    return sections


def pack(parts: list[str], separator: str, max_tokens: int) -> list[str]:
    """Greedily join parts with `separator` while the result stays under max_tokens."""
    pieces, current = [], ""
    for part in parts:
        candidate = f"{current}{separator}{part}" if current else part
        if current and count_tokens(candidate) > max_tokens:
            pieces.append(current)
            current = part
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def split_large_section(text: str, max_tokens: int) -> list[str]:
    """A section bigger than one chunk is split on blank lines (paragraphs).
    A single paragraph that is still too big (a long table or code block)
    is split line by line."""
    paragraphs = []
    for paragraph in text.split("\n\n"):
        if count_tokens(paragraph) > max_tokens:
            paragraphs.extend(pack(paragraph.splitlines(), "\n", max_tokens))
        else:
            paragraphs.append(paragraph)
    return pack(paragraphs, "\n\n", max_tokens)


def chunk_page(text: str) -> list[tuple[str, str]]:
    """Pack small neighbouring sections together; split sections that are too big."""
    chunks: list[tuple[str, str]] = []
    current_heading, current_text = "", ""

    for heading, body in split_into_sections(text):
        if count_tokens(body) > CHUNK_TOKENS:
            if current_text:
                chunks.append((current_heading, current_text))
                current_heading, current_text = "", ""
            chunks.extend((heading, piece) for piece in split_large_section(body, CHUNK_TOKENS))
            continue
        candidate = f"{current_text}\n\n{body}" if current_text else body
        if current_text and count_tokens(candidate) > CHUNK_TOKENS:
            chunks.append((current_heading, current_text))
            current_heading, current_text = heading, body
        else:
            current_heading = current_heading or heading
            current_text = candidate
    if current_text:
        chunks.append((current_heading, current_text))
    return chunks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    documents, chunks = [], []

    for key, cfg in SOURCES.items():
        source_dir = DOCS_DIR / key
        files = sorted(p for p in source_dir.rglob("*") if p.suffix in {".md", ".mdx"})
        for path in files:
            relative = path.relative_to(source_dir).as_posix()
            text = clean_markdown(path.read_text(encoding="utf-8", errors="ignore"))
            if count_tokens(text) < 30:  # skip near-empty stub pages
                continue
            doc_id = f"{key}/{re.sub(r'\.mdx?$', '', relative)}"
            doc = {
                "doc_id": doc_id,
                "source": key,
                "title": page_title(text, path),
                "url": page_url(key, relative),
                "relative_path": relative,
                "text": text,
            }
            documents.append(doc)

            page_chunks = [(h, b) for h, b in chunk_page(text) if count_tokens(b) >= 15]
            for i, (heading, body) in enumerate(page_chunks):
                # Contextual header: source + page title + heading path
                # (the heading path usually starts with the page title; drop the repeat).
                section = heading
                if section.startswith(doc["title"]):
                    section = section[len(doc["title"]):].lstrip(" >")
                header = f"{cfg['label']} > {doc['title']}" + (f" > {section}" if section else "")
                chunks.append({
                    "chunk_id": f"{doc_id}#{i}",
                    "doc_id": doc_id,
                    "source": key,
                    "title": doc["title"],
                    "url": doc["url"],
                    "heading": heading,
                    "text": body,
                    # What we embed and keyword-index: header + body.
                    "search_text": f"{header}\n\n{body}",
                    "tokens": count_tokens(body),
                })
        print(f"[{key}] {sum(d['source'] == key for d in documents)} pages, "
              f"{sum(c['source'] == key for c in chunks)} chunks")

    with DOCUMENTS_FILE.open("w", encoding="utf-8") as f:
        for doc in documents:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
    with CHUNKS_FILE.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    avg = sum(c["tokens"] for c in chunks) / max(len(chunks), 1)
    print(f"Done. {len(documents)} pages -> {len(chunks)} chunks "
          f"(avg {avg:.0f} tokens) written to {CHUNKS_FILE.name}")


if __name__ == "__main__":
    main()
