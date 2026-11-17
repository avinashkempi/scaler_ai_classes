# Nova + Brown: Terminal MCP Client

Interactive terminal client that connects to one or more MCP servers listed in a JSON config file.

```bash
uv run python -m src.client --config mcp_servers_config.json            # Nova (8001) + Brown (8002)
uv run python -m src.client --config mcp_composed_server_config.json    # composed server (8003)
```

Needs `GOOGLE_API_KEY` in `.env` (copy `.env.example`). See `../README.md` for the full walkthrough.
