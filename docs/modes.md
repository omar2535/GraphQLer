# Modes

GraphQLer's work is split into two phases, **compilation** and **fuzzing**, selected with `--mode`.

| Mode | Needs `--url` | What it does |
|---|:-:|---|
| [`compile`](#compile) | yes | Introspection → parsing → dependency resolution → dependency graph → chains |
| [`compile-graph`](#compile-graph) | yes | Compilation without chain generation |
| [`compile-chains`](#compile-chains) | no | (Re-)generate chains from an already compiled graph |
| [`fuzz`](#fuzz) | yes | Execute compiled chains and run detectors |
| [`run`](#run) | yes | `compile` then `fuzz` |
| [`idor`](#idor) | yes | Re-run only the IDOR chains |
| [`single`](#single) | yes | Run one query or mutation |

## Compile

```sh
python -m graphqler --mode compile --url <URL> --path <SAVE_PATH>
```

Runs the full compilation pipeline: introspection → parsing → dependency resolution → dependency graph → fuzzing chains.

- Compiled schema files are written to `<SAVE_PATH>/compiled/`.
- A dependency graph image is written to `<SAVE_PATH>/dependency_graph.png`.
- Fuzzing chains are written to `<SAVE_PATH>/compiled/chains/`.

These files are human-readable and can be edited before fuzzing. Any `UNKNOWNS` in the compiled YAML files can be marked manually; unmarked nodes are still fuzzed, just without a dependency chain.

To also generate [IDOR](idor.md) candidate chains, pass a secondary token:

```sh
python -m graphqler --mode compile --url <URL> --path <SAVE_PATH> --idor-auth 'Bearer <SECONDARY_TOKEN>'
```

## Compile-graph

```sh
python -m graphqler --mode compile-graph --url <URL> --path <SAVE_PATH>
```

Runs introspection, parsing and dependency resolution, then stops before chain generation. Use it to refresh the schema and graph, then run `compile-chains` separately.

## Compile-chains

```sh
python -m graphqler --mode compile-chains --path <SAVE_PATH>
```

Regenerates chains under `compiled/chains/` from the graph already on disk. **No `--url` is required** and no network requests are made — useful for trying `--disable-mutations` or other chain settings without hitting the API again.

## Fuzz

```sh
python -m graphqler --mode fuzz --url <URL> --path <SAVE_PATH>
```

Requires a compiled `<SAVE_PATH>`. While fuzzing, request counts are shown in the console. Results go to:

- `<SAVE_PATH>/stats.txt` and `stats.json` — status codes, coverage and vulnerabilities
- `<SAVE_PATH>/logs/fuzzer.log` — every request and response
- `<SAVE_PATH>/detections/` — one folder per finding

If IDOR chains were generated during compile, they are executed automatically as part of fuzzing.

## Run

```sh
python -m graphqler --mode run --url <URL> --path <SAVE_PATH>
```

Runs `compile` and then `fuzz`.

## IDOR

```sh
python -m graphqler --mode compile --url <URL> --path <SAVE_PATH> --idor-auth 'Bearer <SECONDARY_TOKEN>'
python -m graphqler --mode fuzz    --url <URL> --path <SAVE_PATH>
# Optional: re-run only the IDOR chains
python -m graphqler --mode idor    --url <URL> --path <SAVE_PATH>
```

The `idor` mode re-executes only the IDOR chains, without regular fuzzing — handy for re-testing after a fix. See [IDOR & UAF chains](idor.md).

## Single

```sh
python -m graphqler --mode single --url <URL> --path <SAVE_PATH> --node <NODE_NAME>
```

Runs a single node. `<NODE_NAME>` must be a query or mutation name from the compiled schema.

## Common options

| Option | Purpose |
|---|---|
| `--auth 'Bearer <TOKEN>'` | Primary `Authorization` header. Repeatable as `profile=token` for [multiple profiles](configuration.md#authentication-profiles). |
| `--config <FILE>` | Use a specific [TOML configuration](configuration.md) |
| `--proxy http://127.0.0.1:8080` | Send requests through Burp, ZAP, etc. |
| `--disable-mutations` | Only generate and run Query chains |
| `--subscriptions` | Also fuzz subscriptions over WebSocket |
| `--max-iterations N` | Sweep all chains `N` times |

The complete list is in the [CLI reference](cli.md).
