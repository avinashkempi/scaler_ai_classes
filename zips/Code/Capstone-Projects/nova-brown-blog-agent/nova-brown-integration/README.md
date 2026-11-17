# Nova + Brown Integration

Run the Nova research agent and the Brown writing agent together, so one client can research a topic and write the article end to end.

**Author:** Shivank Agarwal

```
nova-brown-integration/
├── mcp_server/                          # Composed MCP server: mounts Nova + Brown behind one endpoint
│   ├── src/main.py
│   └── mcp_servers_to_compose.json      # Where the composed server finds Nova (8001) and Brown (8002)
└── mcp_client/                          # Terminal client that can talk to several MCP servers
    ├── src/client.py
    ├── mcp_servers_config.json          # Connect to Nova (8001) + Brown (8002) directly
    └── mcp_composed_server_config.json  # Connect to the composed server (8003)
```

## Setup

From the project root:

Install the projects and create the `.env` files as described in the root `README.md`. This client needs `GOOGLE_API_KEY`:

```bash
cp nova-brown-integration/mcp_client/.env.example nova-brown-integration/mcp_client/.env
```

## Option A: client connected to both agents

```bash
# terminal 1: Nova on :8001
cd nova-research-agent/mcp_server && uv run python -m src.server --transport streamable-http --port 8001
# terminal 2: Brown on :8002
cd brown-writing-agent && uv run python -m brown.mcp.server --transport streamable-http --port 8002
# terminal 3
cd nova-brown-integration/mcp_client && uv run python -m src.client --config mcp_servers_config.json
```

Prompts and tools are prefixed with the server name (`nova-research-agent_...`, `brown-writing-workflow_...`). Type `/prompts` to list them.

## Option B: one composed server

Start Nova (:8001) and Brown (:8002) as in Option A, then:

```bash
# terminal 3: Nova + Brown on :8003
cd nova-brown-integration/mcp_server && uv run python -m src.main --transport streamable-http --port 8003
# terminal 4
cd nova-brown-integration/mcp_client && uv run python -m src.client --config mcp_composed_server_config.json
```

The composed server mounts both agents without prefixes and adds one extra prompt, `full_research_and_writing_workflow`, which runs Nova's research workflow and then Brown's article generation on the same folder:

```text
/prompt/full_research_and_writing_workflow?dir_path=/absolute/path/to/article_folder
```

The folder needs an `article_guideline.md`. When the run finishes it contains `research.md` (from Nova) and `article.md` (from Brown).

## Client commands

| Command | What it does |
|---|---|
| `/tools`, `/resources`, `/prompts` | List what the connected servers expose |
| `/prompt/<name>?arg=value` | Load a prompt (e.g. a full workflow) |
| `/resource/<uri>` | Read a resource |
| `/model-thinking-switch` | Toggle the model's thinking output |
| `/quit` | Exit |

Anything else you type is sent to the agent as a normal message.
