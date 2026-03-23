<p align="center">
  <img src="https://raw.githubusercontent.com/omar2535/GraphQLer/main/docs/images/logo.png" />
  <p align="center">The <strong>only</strong> dependency-aware GraphQL API testing tool</p>
</p>

<p align="center">
<a href="https://hub.docker.com/repository/docker/omar2535/graphqler"><img src="https://img.shields.io/docker/image-size/omar2535/graphqler/latest?style=flat&logo=docker"></a>
<a href="https://pypi.org/project/GraphQLer/"><img src="https://img.shields.io/pypi/v/GraphQLer?style=flat&logo=pypi"/></a>
<a href="https://www.python.org/downloads/" target="_blank"><img src="https://img.shields.io/badge/python-3.12-blue" alt="python3.12"/></a>
</br>
<a href="https://github.com/omar2535/GraphQLer/actions/workflows/lint.yml" target="_blank"><img src="https://github.com/omar2535/GraphQLer/actions/workflows/lint.yml/badge.svg" alt="lint" /></a>
<a href="https://github.com/omar2535/GraphQLer/actions/workflows/unit_tests.yml" target="_blank"><img src="https://github.com/omar2535/GraphQLer/actions/workflows/unit_tests.yml/badge.svg?branch=main" alt="unit_test_status" /></a>
<a href="https://github.com/omar2535/GraphQLer/actions/workflows/e2e_tests.yml" target="_blank"><img src="https://github.com/omar2535/GraphQLer/actions/workflows/e2e_tests.yml/badge.svg?branch=main" alt="e2e_test_status" /></a>
</br>
<a href="https://arxiv.org/pdf/2504.13358"><img src="https://img.shields.io/badge/cs.CR-arXiv%3A2504.13358-B31B1B.svg"></a>
<a href="https://github.com/omar2535/GraphQLer/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
</p>

GraphQLer is a cutting-edge tool designed to dynamically test GraphQL APIs with a focus on awareness. It offers a range of sophisticated features that streamline the testing process and ensure robust analysis of GraphQL APIs such as being able to automatically read a schema and run tests against an API using the schema. Furthermore, GraphQLer is aware of dependencies between objects queries and mutations which is then used to perform security tests against APIs.

<div align="center">
  <video src='https://github.com/user-attachments/assets/0c0595a7-d0d9-4554-998a-98d6ebd1fbc2' controls="controls"></video>
</div>

## Key features

- **Request generation**: Automatically generate valid queries and mutations based on the schema *(supports fragments, unions, interfaces, and enums based on the latest [GraphQL-spec](https://spec.graphql.org/October2021/#sec-ID))*
- **Dependency awareness**: Run queries and mutations based on their natural dependencies
- **Resource tracking**: Keep track of any objects seen in the API for future use and reconnaisance
- **Error correction**: Try and fix requests so that the GraphQL API accepts them
- **Vulnerability detection output**: Every confirmed vulnerability writes a `detections/` folder containing `raw_log.txt` (full request/response chain) and `summary.txt` (chain steps + final payload + response)
- **IDOR detection**: Automatically detect insecure direct object reference vulnerabilities using dual-profile chain replay
- **Statistics collection**: Shows your results in a easy-to-read file
- **Ease of use**: All you need is the endpoint and the authentication token if needed
- **Customizability**: Change the configuration file to suit your needs, proxy requests through Burp or ZAP if you want

## Getting started

Quick installation can be done either with [pip](https://pypi.org/project/GraphQLer/):

```sh
pip install GraphQLer
python -m graphqler --help
```

or [docker](https://hub.docker.com/repository/docker/omar2535/graphqler/general):

```sh
docker pull omar2535/graphqler:latest
docker run --rm omar2535/graphqler --help
```

For a more in-depth guide, check out the [installation guide](./docs/installation.md).

## Usage

```sh
❯ python -m graphqler --help
usage: __main__.py [-h] [--url URL] [--path PATH] [--config CONFIG] --mode
                   {compile,compile-graph,compile-chains,fuzz,idor,run,single} [--auth AUTH] [--idor-auth IDOR_AUTH]
                   [--proxy PROXY] [--node NODE] [--plugins-path PLUGINS_PATH] [--use-llm] [--llm-report]
                   [--llm-model LLM_MODEL] [--llm-api-key LLM_API_KEY] [--llm-base-url LLM_BASE_URL]
                   [--llm-max-retries LLM_MAX_RETRIES] [--disable-mutations] [--no-objects-bucket]
                   [--no-dependency-graph] [--max-iterations MAX_ITERATIONS] [--allow-deletion] [--subscriptions]
                   [--version]

options:
  -h, --help            show this help message and exit
  --url URL             remote host URL (required for all modes except compile-chains)
  --path PATH           directory location for files to be saved-to/used-from. Defaults to graphqler-output
  --config CONFIG       TOML configuration file for the program
  --mode {compile,compile-graph,compile-chains,fuzz,idor,run,single}
                        mode to run the program in
  --auth AUTH           authentication token(s). Can be 'token' or 'profile=token'. Multiple allowed.
  --idor-auth IDOR_AUTH
                        secondary (attacker) auth token for chain-based IDOR testing. Example: 'Bearer secondtoken'
  --proxy PROXY         proxy to use for requests (ie. http://127.0.0.1:8080)
  --node NODE           node to run (only used in single mode)
  --plugins-path PLUGINS_PATH
                        path to plugins directory
  --use-llm             enable LLM-powered features: dependency graph inference, endpoint classification, and IDOR
                        chain classification (requires LLM_MODEL and credentials)
  --llm-report          generate an LLM vulnerability report (report.md) after fuzzing completes — requires --use-llm
  --llm-model LLM_MODEL
                        litellm model string, e.g. 'gpt-4o-mini', 'ollama/llama3',
                        'anthropic/claude-3-5-haiku-20241022'
  --llm-api-key LLM_API_KEY
                        API key for the LLM provider (or set OPENAI_API_KEY / ANTHROPIC_API_KEY env var)
  --llm-base-url LLM_BASE_URL
                        custom base URL for LLM endpoint (required for Ollama and LiteLLM proxies)
  --llm-max-retries LLM_MAX_RETRIES
                        number of retries when LLM returns non-JSON (default: 2)
  --disable-mutations   only generate and run Query chains — all Mutation nodes are excluded from fuzzing
  --no-objects-bucket   ablation: disable the objects bucket — requests carry no state from prior responses
  --no-dependency-graph
                        ablation: disable dependency-graph chain ordering — all nodes run independently without
                        chaining
  --max-iterations MAX_ITERATIONS
                        number of times to iterate through all chains (default: 1)
  --allow-deletion      remove objects from the bucket when a DELETE mutation succeeds (default: off)
  --subscriptions       enable fuzzing of GraphQL subscriptions via WebSocket (disabled by default — requires
                        WebSocket support on the target)
  --version             display version
```

Below will be the steps on how you can use this program to test your GraphQL API. The usage is split into 2 phases, **compilation** and **fuzzing**.

- **Compilation mode**: Responsible for running an *introspection query* against the given API, resolving dependencies between objects/queries/mutations, generating the dependency graph, and pre-generating fuzzing chains.
- **Fuzzing mode**: Responsible for executing the pre-generated chains against the API and collecting results.

The compile step can be broken into two finer sub-modes:

- **compile-graph**: Runs only the introspection, parsing, and dependency-resolution steps — stops before chain generation.
- **compile-chains**: (Re-)generates fuzzing chains from an already-compiled graph without making any network requests. Useful when you want to tweak `DISABLE_MUTATIONS` or the chain strategy without re-running introspection.

A third mode is also included for ease of use, called **run** mode — this runs both compilation and fuzzing in a single command.

The **idor** mode detects insecure direct object reference (IDOR) vulnerabilities using multi-profile chain replay. Pass `--idor-auth <SECONDARY_TOKEN>` during **compile** to generate IDOR candidate chains (`compiled/chains/idor.yml`). IDOR detection then runs automatically during **fuzz** mode — any object accessible to the secondary (attacker) profile is flagged. The standalone **idor** mode re-executes those chains without running regular fuzzing, and is useful for targeted re-testing.

### Compile mode

```sh
python -m graphqler --mode compile --url <URL> --path <SAVE_PATH>
```

Runs the full compilation pipeline: introspection → parsing → dependency resolution → dependency graph → fuzzing chains. After compiling, you can view the compiled results in `<SAVE_PATH>/compiled`. A dependency graph image (`dependency_graph.png`) is also generated for inspection. Fuzzing chains are saved under `<SAVE_PATH>/compiled/chains/` — these files are human-readable and can be edited before fuzzing. Any `UNKNOWNS` in the compiled `.yaml` files can be manually marked; however, if not marked the fuzzer will still run them but just without using a dependency chain.

To enable IDOR detection, pass `--idor-auth` during compile:

```sh
python -m graphqler --mode compile --url <URL> --path <SAVE_PATH> --idor-auth 'Bearer <SECONDARY_TOKEN>'
```

This generates IDOR candidate chains in `compiled/chains/idor.yml` alongside the regular chains.

### Compile-graph mode

```sh
python -m graphqler --mode compile-graph --url <URL> --path <SAVE_PATH>
```

Runs only the introspection, parsing, and dependency-resolution steps. Stops before chain generation. Use this when you only want to refresh the schema and graph, then run `compile-chains` separately (e.g. to experiment with different chain settings without hitting the API again).

### Compile-chains mode

```sh
python -m graphqler --mode compile-chains --path <SAVE_PATH>
```

(Re-)generates fuzzing chains from an already-compiled dependency graph. **No `--url` is required** — all data is read from disk. Run this after `compile` or `compile-graph` to regenerate chains under `compiled/chains/` with different settings (e.g. `--disable-mutations` or a custom `CHAINS_FILE_NAME` in your config).

### Fuzz mode

```sh
python -m graphqler --mode fuzz --url <URL> --path <SAVE_PATH>
```

While fuzzing, statistics related to the GraphQL API and any ongoing request counts are logged in the console. Any request return codes are written to `<SAVE_PATH>/stats.txt`. All logs during fuzzing are kept in `<SAVE_PATH>/logs/fuzzer.log`. The log file will tell you exactly which requests are sent to which endpoints, and what the response was. This can be used for further result analysis. If IDOR chains were generated during compile, the fuzzer automatically tests them and writes detection results to `<SAVE_PATH>/detections/`.

### IDOR Checking mode

```sh
python -m graphqler --mode compile --url <URL> --path <SAVE_PATH> --idor-auth 'Bearer <SECONDARY_TOKEN>'
python -m graphqler --mode fuzz --url <URL> --path <SAVE_PATH>
# Optional: re-run IDOR chains only (no regular fuzzing)
python -m graphqler --mode idor --url <URL> --path <SAVE_PATH>
```

[Insecure direct object reference (IDOR)](https://portswigger.net/web-security/access-control/idor) detection works via multi-profile chain replay. During **compile**, `--idor-auth` enables generation of IDOR candidate chains: endpoints that create or expose user-scoped objects are identified via heuristics (and optionally an LLM classifier), then split into primary-profile steps (authenticated user) and secondary-profile steps (attacker token). These chains are saved to `compiled/chains/idor.yml`.

During **fuzz**, the `IDORChainDetector` executes each IDOR chain — the primary profile creates or retrieves the object, then the secondary profile attempts to access it. Any data returned to the secondary profile is flagged as a potential IDOR vulnerability and written to `<SAVE_PATH>/detections/IDOR/<endpoint>/`.

The standalone **idor** mode re-executes only the IDOR chains without running regular fuzzing. This is useful for targeted re-testing after fixing an issue, or when you only want to check access-control without the overhead of a full fuzz run.

### Run mode

Runs both the Compile mode and Fuzz mode

```sh
python -m graphqler --mode run --url <URL> --path <SAVE_PATH>
```

### Single mode

Runs a single node (make sure it exists in the list of queries or mutations)

```sh
python -m graphqler --url <URL> --path <SAVE_PATH> --config <CUSTOM_CONFIG>> --proxy <CUSTOM_PROXY> --mode single --node <NODE_NAME>
```

## Advanced features

There are also varaibles that can be modified with the `--config` flag as a TOML file (see `/examples/config.toml` for an example). These correspond to specific features implemented in GraphQLer, and can be tuned to your liking.

| Variable Name | Variable Description | Variable Type | Default |
|---------------|---------------------|---------------|---------------|
| MAX_LEVENSHTEIN_THRESHOLD | The levenshtein distance between objects and object IDs | Integer | 20 |
| MAX_OBJECT_CYCLES | Max number of times the same object should be materialized in the same query/mutation | Integer | 3 |
| MAX_OUTUPT_SELECTOR_DEPTH | Max depth the query/mutation's output should be expanded (such as the case of infinitely recursive selectors) | Integer | 3 |
| USE_OBJECTS_BUCKET | Whether or not to store object IDs for future use | Boolean | True |
| USE_DEPENDENCY_GRAPH | Whether or not to use the dependency-aware feature | Boolean | True |
| ALLOW_DELETION_OF_OBJECTS | Whether or not to allow deletions from the objects bucket | Boolean | False |
| MAX_FUZZING_ITERATIONS | Maximum number of fuzzing payloads to run on a node | Integer | 5 |
| MAX_TIME | The maximum time to run in seconds | Integer | 3600 |
| TIME_BETWEEN_REQUESTS | Max time to wait between requests in seconds | Integer | 0.001 |
| DEBUG | Debug mode | Boolean | False |
| Custom Headers | Custom headers to be sent along with each request | Object | `Accept = "application/json"` |
| SKIP_MAXIMAL_PAYLOADS | Whether or not to send a payload with all the possible outputs | Boolean | False |
| SKIP_DOS_ATTACKS | Whether or not to skip DOS attacks(defaults to true to not DOS the service) | Boolean | True |
| SKIP_INJECTION_ATTACKS | Whether or not to skip injection attacks | Boolean | False |
| SKIP_MISC_ATTACKS | Whether or not to skip miscillaneous attacks | Boolean | False |
| SKIP_NODES | Nodes to skip (query or mutation names) | List | [] |
| DISABLE_MUTATIONS | Only generate and run Query chains — all Mutation nodes are excluded from chain generation and fuzzing. Can also be set via `--disable-mutations` CLI flag. | Boolean | False |
| IDOR_SECONDARY_AUTH | Secondary (attacker) authentication token for IDOR chain detection (e.g. `"Bearer token2"`). If not set, the IDOR chain phase is skipped. | String | None |

## AI Features

LLM Enabled compilation (using ollama as an example):

```sh
uv run graphqler --url http://localhost:4000/graphql --mode run --use-llm --llm-model ollama/qwen3.5:9b --llm-base-url http://localhost:11434
```


### Plugins

You can also implement your own plugins for custom authentication (ie. short token lifetimes). See more in the [docs](https://github.com/omar2535/GraphQLer/tree/main/docs).
