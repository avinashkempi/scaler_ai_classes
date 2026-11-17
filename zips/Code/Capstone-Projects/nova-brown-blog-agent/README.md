# Nova + Brown: Multi-Agent Blog Writer

**Author:** Shivank Agarwal · Future with Shivank

Two AI agents that work together to research and write technical blog articles:

- **Nova** (research agent) reads your `article_guideline.md`, collects sources (web search, scraped pages, GitHub repos, YouTube transcripts, local files), filters them by quality, and writes a single `research.md`.
- **Brown** (writing agent) takes the guideline + research, generates diagrams, writes a draft, then reviews and edits it in a loop until it meets the guideline and the writing profiles. Output: `article.md`.

Both agents are **MCP servers**, so you can drive them from the included terminal clients or from any MCP client (Claude Desktop, Cursor, Claude Code).

**Start here:** open `docs/problem_statement.html` (the project brief) and then `docs/solution.html` (a detailed walkthrough of the design, the code and what every run looks like) in your browser.

```
article_guideline.md ──► Nova (research) ──► research.md ──► Brown (writing) ──► article.md
```

## Project layout

```
nova-brown-blog-agent/
├── docs/                       # problem statement + detailed solution walkthrough (HTML)
├── nova-research-agent/        # Nova: research agent
│   ├── mcp_server/             #   MCP server with the research tools
│   ├── mcp_client/             #   interactive terminal client (runs Nova in-process)
│   └── data/                   #   sample article guidelines to research
├── brown-writing-agent/        # Brown: writing agent (LangGraph + FastMCP)
│   ├── src/brown/              #   workflows, nodes, entities, MCP server, evals
│   ├── configs/                #   model + review-loop settings (gemini-flash.yaml is the default)
│   ├── inputs/profiles/        #   writing style profiles + author persona (shivank_agarwal.md)
│   ├── inputs/examples/        #   example articles used as style references
│   ├── inputs/tests/           #   sample input folders to try Brown on
│   └── inputs/evals/           #   evaluation dataset (Opik)
├── nova-brown-integration/     # Run Nova + Brown together
│   ├── mcp_server/             #   one composed MCP server exposing both agents
│   └── mcp_client/             #   terminal client that talks to both agents
├── .mcp.json                   # Ready-made config for MCP clients (stdio)
├── Makefile                    # Shortcuts for the commands below
└── ruff.toml                   # Lint/format settings
```

Each folder with a `pyproject.toml` is its own `uv` project with its own virtual environment.

## Requirements

- [`uv`](https://docs.astral.sh/uv/) (it downloads the right Python version for each project: 3.12 for Nova, 3.14 for Brown)
- GNU Make (optional, for the shortcuts)
- API keys:

| Key | Used by | Required? |
|---|---|---|
| `GOOGLE_API_KEY` | Nova, Brown, clients (Gemini models) | Yes |
| `PPLX_API_KEY` | Nova web search (default provider) | Yes for Nova |
| `FIRECRAWL_API_KEY` | Nova web scraping | Yes for Nova |
| `TAVILY_API_KEY` | Nova web search, if `WEB_SEARCH_PROVIDER=tavily` | Optional |
| `GITHUB_TOKEN` | Nova, private GitHub repos | Optional |
| `OPIK_API_KEY` | Tracing + evals in Opik | Optional |

## Setup

```bash
make install          # runs `uv sync` in all five projects
```

Create a `.env` in every project you use, from its `.env.example`:

```bash
cp nova-research-agent/mcp_server/.env.example     nova-research-agent/mcp_server/.env
cp nova-research-agent/mcp_client/.env.example     nova-research-agent/mcp_client/.env
cp brown-writing-agent/.env.example                brown-writing-agent/.env
cp nova-brown-integration/mcp_client/.env.example  nova-brown-integration/mcp_client/.env
```

Then fill in your keys.

## Run

### 1. Brown only: write an article from existing research

```bash
make brown-generate DIR_PATH=inputs/tests/00_sample_tiny
```

The folder must contain `article_guideline.md` and `research.md`. Brown saves every draft (`article_000.md`, `article_001.md`, ...) and the final `article.md` in the same folder. See `brown-writing-agent/README.md` for editing a whole article or a selected range of lines.

### 2. Nova only: research a topic

```bash
make nova-client
```

At the `👤 You:` prompt:

```text
/prompt/full_research_instructions_prompt
The research folder is /absolute/path/to/nova-research-agent/data/research_function_calling. Run the complete workflow.
```

Nova writes `research.md` into that folder. See `nova-research-agent/README.md` for details.

### 3. Nova + Brown together: research and write in one go

Start both agents as HTTP servers (one terminal each):

```bash
make nova-http        # Nova  on http://localhost:8001/mcp
make brown-http       # Brown on http://localhost:8002/mcp
```

Then, in a third terminal:

```bash
make client
```

Or expose both agents behind one endpoint with the composed server:

```bash
make composed-http    # Nova + Brown on http://localhost:8003/mcp
make client-composed
```

In the client, load the end-to-end prompt and give it a folder that contains an `article_guideline.md`:

```text
/prompt/full_research_and_writing_workflow?dir_path=/absolute/path/to/your/article_folder
```

(With `make client`, prompt names carry the server prefix; run `/prompts` to see them.)

### 4. From Claude Desktop, Cursor or Claude Code

`.mcp.json` at the project root starts Nova and Brown over stdio. Open the project in Claude Code or Cursor, or copy the two entries into your client's MCP config (use absolute paths there).

## Tests and quality checks

```bash
make test     # Brown unit + integration tests (fake models, no API calls)
make lint     # ruff format check + lint for all projects
```

## How Brown writes

1. Loads the guideline, research, writing profiles and example articles.
2. Generates the Mermaid diagrams the guideline asks for.
3. Writes a first draft.
4. Reviews the draft against the guideline and profiles, then edits it. Repeats up to `num_reviews` times (stops early when the reviewer has no comments).

Change models, the number of review rounds and other settings in `brown-writing-agent/configs/gemini-flash.yaml`. The author voice comes from `brown-writing-agent/inputs/profiles/character_profiles/shivank_agarwal.md`.

## License

Apache License 2.0. See `LICENSE`.
