"""MCP (Model Context Protocol) server for GraphQLer.

This package exposes GraphQLer's compile, fuzz, and run operations as MCP tools,
allowing AI assistants to drive GraphQL API security testing directly.

Install the optional MCP dependency before using:

    pip install GraphQLer[mcp]

Launch the MCP server (stdio transport, compatible with Claude Desktop, Cursor, etc.):

    python -m graphqler --mcp
"""
