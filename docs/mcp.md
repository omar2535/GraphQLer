# MCP server

GraphQLer exposes compile, fuzz and run as [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) tools, so AI assistants such as Claude Desktop can drive security testing directly.

## Installation

```sh
pip install "GraphQLer[mcp]"
```

## Starting the server

```sh
# stdio transport (default — use this for Claude Desktop and most MCP clients)
python -m graphqler --mcp

# Other transports
python -m graphqler --mcp --mcp-transport sse
python -m graphqler --mcp --mcp-transport streamable-http
python -m graphqler --mcp --mcp-transport http
```

The `graphqler-mcp` script is equivalent to `python -m graphqler --mcp` with the default stdio transport. It accepts no options; use the `python -m graphqler --mcp …` form for other transports.

## Client configuration

For clients that launch servers from a JSON config (such as Claude Desktop):

```json
{
  "mcpServers": {
    "graphqler": {
      "command": "graphqler-mcp"
    }
  }
}
```

## Tools

| Tool | Description |
|---|---|
| `compile(url, path, auth)` | Introspect the API, build the dependency graph and generate fuzzing chains |
| `fuzz(url, path, auth)` | Fuzz a previously compiled API; returns success/failure counts and vulnerabilities |
| `run(url, path, auth)` | `compile` then `fuzz` |

`path` defaults to `graphqler-output`. `auth` is an optional `Authorization` header value, e.g. `"Bearer mytoken"`. Calls are serialised — only one pipeline runs at a time.

## Resources

| Resource URI | Description |
|---|---|
| `graphqler://schema/{path}` | Compiled schema information (queries, mutations, objects, …) as JSON |
| `graphqler://results/{path}` | Fuzzing results and vulnerability findings as JSON |
