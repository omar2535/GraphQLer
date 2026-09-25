# CLI reference

```sh
python -m graphqler [options] --mode <MODE>
```

Special invocations:

| Invocation | Effect |
|---|---|
| `python -m graphqler` | Opens the [interactive TUI](tui.md) |
| `python -m graphqler --version` | Prints the installed version |
| `python -m graphqler --mcp [--mcp-transport T]` | Starts the [MCP server](mcp.md); `--mode` is not required |

## Target and I/O

| Flag | Description |
|---|---|
| `--mode {compile,compile-graph,compile-chains,fuzz,idor,run,single}` | **Required.** See [Modes](modes.md). |
| `--url URL` | GraphQL endpoint. Required for all modes except `compile-chains`. |
| `--path PATH` | Output directory. Default: `graphqler-output`. |
| `--config CONFIG` | TOML configuration file. If omitted, `<PATH>/config.toml` is used when present, otherwise generated. |
| `--node NODE` | Query/mutation to run in `single` mode. |
| `--plugins-path PLUGINS_PATH` | Directory containing [plugins](plugins.md). |
| `--proxy PROXY` | HTTP proxy, e.g. `http://127.0.0.1:8080`. TLS verification is disabled when a proxy is set. |

## Authentication

| Flag | Description |
|---|---|
| `--auth AUTH` | `Authorization` header value. Either `token` (primary profile) or `profile=token`. Repeatable. |
| `--idor-auth IDOR_AUTH` | Secondary (attacker) token for [IDOR chains](idor.md), e.g. `'Bearer secondtoken'`. |

## Fuzzing behaviour

| Flag | Description |
|---|---|
| `--disable-mutations` | Only generate and run Query chains. |
| `--no-detections` | Disable injection, misc, DoS and enumeration detections. |
| `--max-iterations N` | Number of sweeps through all chains (default: 1). |
| `--allow-deletion` | Remove objects from the bucket when a DELETE mutation succeeds. |
| `--subscriptions` | Fuzz subscriptions over WebSocket (off by default). |
| `--no-endpoint-results` | Do not write per-endpoint result files. |
| `--classic-coverage` | Count responses without data as successes (`NO_DATA_COUNT_AS_SUCCESS = true`). |
| `--debug` | Run the fuzzer in a thread instead of a subprocess so `pdb`/`breakpoint()` work. |

## Ablation (research)

| Flag | Description |
|---|---|
| `--no-objects-bucket` | Requests carry no state from prior responses. |
| `--no-dependency-graph` | Run all nodes independently without chain ordering. |

## LLM

See [LLM features](llm.md).

| Flag | Description |
|---|---|
| `--use-llm` | Enable LLM features (dependency inference, endpoint classification, IDOR/UAF chain classification). |
| `--no-llm-compilation` | Disable the LLM during compilation even with `--use-llm`. |
| `--no-llm-fuzzing` | Disable the LLM during fuzzing even with `--use-llm`. |
| `--llm-report` | Write an LLM vulnerability report (`report.md`) after fuzzing. Requires `--use-llm`. |
| `--llm-model LLM_MODEL` | [litellm](https://docs.litellm.ai/docs/providers) model string, e.g. `gpt-4o-mini`, `ollama/llama3`. |
| `--llm-api-key LLM_API_KEY` | Provider API key (or set `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`). |
| `--llm-base-url LLM_BASE_URL` | Custom endpoint; required for Ollama and LiteLLM proxies. |
| `--llm-max-retries N` | Retries when the LLM returns non-JSON (default: 2). |

## MCP

| Flag | Description |
|---|---|
| `--mcp` | Launch the MCP server (requires `pip install "GraphQLer[mcp]"`). |
| `--mcp-transport TRANSPORT` | `stdio` (default), `sse`, `streamable-http` or `http`. |

## Precedence

1. Built-in defaults
2. The configuration file (`--config`, else `<PATH>/config.toml`)
3. CLI flags — always win

The fully resolved configuration is written back to `<PATH>/config.toml` on every run, so the output directory always records the settings that produced it.
