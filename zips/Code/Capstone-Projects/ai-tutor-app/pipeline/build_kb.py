"""
Step 3 of the data pipeline: build the browsable knowledge base (KB).

Author: Shivank Agrawal
Project: AI Tutor (Agentic RAG) - Future with Shivank

Vector search gives the agent "top-k similar passages". The KB gives it a
second way to find things: browse the docs like files on disk with read-only
commands (cat, rg, grep, find ...). The KB has three layers:

    data/kb/raw/        one markdown file per doc page, with a small header
                        (title, url, source). This is the ground truth.
    data/kb/generated/  machine indexes: a manifest of every page, every
                        heading with its line number, and code symbols
                        (LoraConfig, SFTTrainer, function_tool ...).
    data/kb/wiki/       navigation pages: a start page, one page per source
                        (overview written by the LLM) and one page per topic.

The wiki idea follows Andrej Karpathy's "LLM wiki": keep a small, readable map
over the immutable sources, so the agent orients itself in one `cat` instead
of re-discovering the corpus on every question.

Run from the project root (needs OPENAI_API_KEY for the source overviews):
    python -m pipeline.build_kb
"""

import json
import re
from collections import defaultdict

from openai import OpenAI

from app.config import CHAT_MODEL, DOCUMENTS_FILE, KB_DIR, SOURCES

RAW_DIR, WIKI_DIR, GEN_DIR = KB_DIR / "raw", KB_DIR / "wiki", KB_DIR / "generated"
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
CODE_RE = re.compile(r"```.*?```|`[^`\n]+`", re.DOTALL)
CLASS_RE = re.compile(r"\b[A-Z][A-Za-z0-9]*[a-z][A-Za-z0-9]*\b")
FUNC_RE = re.compile(r"\b([a-z_][a-z0-9_]{2,})\(")
NOT_SYMBOLS = {"True", "False", "None", "Python", "Example", "Note", "Optional", "List", "Dict"}

# Topic pages: a page joins a topic when the keyword is in its title or shows
# up often in its text.
TOPICS = {
    "lora-and-adapters": ("lora", "qlora", "adapter", "loraconfig"),
    "quantization": ("quantization", "quantized", "bitsandbytes", "4-bit", "8-bit"),
    "supervised-fine-tuning": ("sft", "sfttrainer", "supervised fine-tuning", "fine-tune"),
    "preference-and-rl-training": ("dpo", "grpo", "ppo", "reward model", "preference"),
    "agents-and-tools": ("agent", "function_tool", "tool call", "tools"),
    "multi-agent-and-handoffs": ("handoff", "agents as tools", "orchestrat", "multi-agent"),
    "guardrails": ("guardrail",),
    "sessions-and-memory": ("session", "memory", "conversation history"),
    "tracing-and-debugging": ("tracing", "trace", "debug"),
    "merging-and-inference": ("merge_and_unload", "merging", "inference", "vllm"),
}


def raw_path(doc: dict) -> str:
    """Path of a page inside the KB, e.g. raw/docs/peft/developer_guides/lora.md"""
    return f"raw/docs/{doc['doc_id']}.md"


def write(relative: str, content: str) -> None:
    path = KB_DIR / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Layer 1: raw/
# ---------------------------------------------------------------------------
def build_raw(documents: list[dict]) -> None:
    for doc in documents:
        header = (
            "---\n"
            f"title: {json.dumps(doc['title'])}\n"
            f"url: {doc['url']}\n"
            f"source: {doc['source']}\n"
            f"doc_id: {doc['doc_id']}\n"
            "---\n\n"
        )
        write(raw_path(doc), header + doc["text"] + "\n")
    print(f"raw/        {len(documents)} pages")


# ---------------------------------------------------------------------------
# Layer 2: generated/ (machine indexes)
# ---------------------------------------------------------------------------
def build_generated(documents: list[dict]) -> None:
    manifest, headings, symbols = [], [], set()
    for doc in documents:
        path = raw_path(doc)
        manifest.append({"doc_id": doc["doc_id"], "source": doc["source"],
                         "title": doc["title"], "url": doc["url"], "path": path})

        text = (KB_DIR / path).read_text(encoding="utf-8")
        in_code = False
        for number, line in enumerate(text.splitlines(), start=1):
            if line.lstrip().startswith("```"):
                in_code = not in_code
            match = None if in_code else HEADING_RE.match(line)
            if match:
                headings.append({"path": path, "line": number,
                                 "level": len(match.group(1)), "heading": match.group(2)})

        for code in CODE_RE.findall(doc["text"]):
            for name in CLASS_RE.findall(code) + FUNC_RE.findall(code):
                if name not in NOT_SYMBOLS:
                    symbols.add((name, path))

    write("generated/corpus_manifest.jsonl", "".join(json.dumps(r) + "\n" for r in manifest))
    write("generated/headings.jsonl", "".join(json.dumps(h) + "\n" for h in headings))
    write("generated/symbols.tsv", "symbol\tpath\n" + "".join(f"{s}\t{p}\n" for s, p in sorted(symbols)))
    print(f"generated/  {len(manifest)} manifest rows, {len(headings)} headings, {len(symbols)} symbols")


# ---------------------------------------------------------------------------
# Layer 3: wiki/ (navigation)
# ---------------------------------------------------------------------------
def write_source_overview(client: OpenAI, key: str, docs: list[dict]) -> str:
    """Ask the LLM to write a short map of one documentation source."""
    listing = "\n".join(
        f"- {raw_path(d)} | {d['title']} | {d['text'][:180].replace(chr(10), ' ')}"
        for d in docs
    )
    prompt = f"""You are writing a navigation page that an AI tutor agent reads
before answering student questions about {SOURCES[key]['label']}.

Here is every page in this documentation (path | title | first words):
{listing}

Write markdown with exactly these parts:
1. A 3-4 sentence paragraph: what this documentation covers and who it is for.
2. "## Start here": the 5 most useful pages for a beginner, as bullets
   "- `<path>`: <why read it>".
3. "## Which page answers which question": 8 bullets mapping a typical
   student question to the best page, as "- <question> -> `<path>`".
Use only paths from the list above. No title line, no extra sections."""
    response = client.responses.create(model=CHAT_MODEL, input=prompt)
    return response.output_text.strip()


def build_wiki(documents: list[dict]) -> None:
    client = OpenAI()
    by_source = defaultdict(list)
    for doc in documents:
        by_source[doc["source"]].append(doc)

    # One page per source: LLM overview + the full list of pages.
    for key, docs in by_source.items():
        print(f"wiki/       writing overview for {key} with {CHAT_MODEL} ...")
        overview = write_source_overview(client, key, docs)
        pages = "\n".join(f"- `{raw_path(d)}`: {d['title']}" for d in docs)
        write(f"wiki/frameworks/{key}.md",
              f"# {SOURCES[key]['label']}\n\n"
              f"<!-- Overview written by {CHAT_MODEL}; page list generated. -->\n\n"
              f"{overview}\n\n## All {len(docs)} pages\n\n{pages}\n")

    # One page per topic: pages that match the topic keywords, across sources.
    topic_counts = {}
    for topic, keywords in TOPICS.items():
        scored = []
        for doc in documents:
            title, text = doc["title"].lower(), doc["text"].lower()
            mentions = sum(text.count(k) for k in keywords)
            in_title = any(k in title for k in keywords)
            if in_title or mentions >= 4:
                scored.append((10 * in_title + min(mentions, 30), doc))
        scored.sort(key=lambda item: -item[0])
        top = [doc for _, doc in scored[:25]]
        topic_counts[topic] = len(top)
        lines = "\n".join(f"- `{raw_path(d)}` ({d['source']}): {d['title']}" for d in top)
        write(f"wiki/topics/{topic}.md",
              f"# Topic: {topic.replace('-', ' ')}\n\n"
              f"Pages that discuss this topic, most relevant first:\n\n{lines}\n")

    # The start page the agent reads first.
    source_lines = "\n".join(
        f"- **{SOURCES[k]['label']}** (`{k}`): {len(by_source[k])} pages -> `wiki/frameworks/{k}.md`"
        for k in by_source
    )
    topic_lines = "\n".join(
        f"- {t.replace('-', ' ')} -> `wiki/topics/{t}.md` ({n} pages)" for t, n in topic_counts.items()
    )
    write("wiki/index.md", f"""# AI Tutor knowledge base: start here

This KB mirrors the documentation the tutor teaches from.

- `raw/docs/<source>/...md`: the real pages (ground truth, cite these).
- `wiki/`: navigation pages like this one (never cite these).
- `generated/`: machine indexes for exact lookups.

## Sources

{source_lines}

## Topics

{topic_lines}

## Exact lookups

- Class or function name: `rg -n -m 20 "LoraConfig" generated/symbols.tsv`
- Section headings: `rg -n -m 20 "rank" generated/headings.jsonl`
- Page titles and URLs: `rg -n -m 20 "quickstart" generated/corpus_manifest.jsonl`
""")
    print(f"wiki/       index + {len(by_source)} source pages + {len(TOPICS)} topic pages")


def main() -> None:
    documents = [json.loads(line) for line in DOCUMENTS_FILE.open(encoding="utf-8")]
    build_raw(documents)
    build_generated(documents)
    build_wiki(documents)
    print("Done. Knowledge base ready in data/kb/")


if __name__ == "__main__":
    main()
