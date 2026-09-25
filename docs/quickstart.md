# Quickstart

This walks through testing a GraphQL API end to end. Replace `<URL>` with your GraphQL endpoint (for example `http://localhost:4000/graphql`).

!!! warning "Only test APIs you are authorised to test"

    GraphQLer sends mutations and attack payloads. Point it at development or staging environments you own.

## 1. Compile and fuzz in one step

```sh
python -m graphqler --mode run --url <URL> --path ./my-api-output
```

`run` performs [compilation](modes.md#compile) followed by [fuzzing](modes.md#fuzz). Everything is written to `./my-api-output` (default: `graphqler-output`).

If the API needs authentication, pass the `Authorization` header value:

```sh
python -m graphqler --mode run --url <URL> --auth 'Bearer <TOKEN>'
```

## 2. Inspect the results

| File | What to look at |
|---|---|
| `dependency_graph.png` | How GraphQLer linked objects, queries and mutations |
| `stats.txt` | Endpoint coverage, HTTP status codes and detected vulnerabilities |
| `detections/` | One folder per finding with `summary.txt` and the full `raw_log.txt` |
| `logs/fuzzer.log` | Every request sent and response received |

See [Output files](output.md) for the full layout.

## 3. Iterate

Compilation and fuzzing are separate so you can tweak between them:

```sh
python -m graphqler --mode compile --url <URL> --path ./my-api-output
# edit ./my-api-output/compiled/*.yml or ./my-api-output/config.toml
python -m graphqler --mode fuzz --url <URL> --path ./my-api-output
```

A `config.toml` is created in the output directory on first run and reused afterwards — see [Configuration](configuration.md).

## Prefer a UI?

Run with no arguments to open the [interactive TUI](tui.md):

```sh
python -m graphqler
```
