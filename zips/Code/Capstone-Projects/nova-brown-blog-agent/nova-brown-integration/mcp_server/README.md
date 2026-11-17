# Nova + Brown: Composed MCP Server

One MCP server that mounts the Nova research agent and the Brown writing agent and adds the `full_research_and_writing_workflow` prompt.

It connects to Nova and Brown over HTTP using `mcp_servers_to_compose.json` (Nova on port 8001, Brown on 8002), so start those first.

```bash
uv run python -m src.main --transport streamable-http --port 8003
```

Pass `--config path/to/other.json` to compose a different set of servers. See `../README.md` for the full walkthrough.
