<p align="center">
  <img src="https://raw.githubusercontent.com/omar2535/GraphQLer/main/docs/images/logo.png" />
  <p align="center">The <strong>only</strong> dependency-aware GraphQL API testing tool!</p>
</p>

<p align="center">
<a href="https://hub.docker.com/repository/docker/omar2535/graphqler"><img src="https://img.shields.io/docker/image-size/omar2535/graphqler/latest?style=flat&logo=docker"></a>
<a href="https://pypi.org/project/GraphQLer/"><img src="https://img.shields.io/pypi/v/GraphQLer?style=flat&logo=pypi"/></a>
<a href="https://www.python.org/downloads/" target="_blank"><img src="https://img.shields.io/badge/python-3.12-blue" alt="python3.12"/></a>
<a href="https://codeclimate.com/github/omar2535/GraphQLer/maintainability" target="_blank"><img src="https://api.codeclimate.com/v1/badges/a34db44e691904955ded/maintainability" alt="Maintainability" /></a>
<a href="https://github.com/omar2535/GraphQLer/actions/workflows/lint.yml" target="_blank"><img src="https://github.com/omar2535/GraphQLer/actions/workflows/lint.yml/badge.svg" alt="lint" /></a>
<a href="https://github.com/omar2535/GraphQLer/actions/workflows/unit_tests.yml" target="_blank"><img src="https://github.com/omar2535/GraphQLer/actions/workflows/unit_tests.yml/badge.svg?branch=main" alt="unit_test_status" /></a>
<a href="https://github.com/omar2535/GraphQLer/actions/workflows/integration_tests.yml" target="_blank"><img src="https://github.com/omar2535/GraphQLer/actions/workflows/integration_tests.yml/badge.svg?branch=main" alt="integration_test_status" /></a>
<a href="https://sonarcloud.io/summary/new_code?id=omar2535_GraphQLer" target="_blank"><img src="https://sonarcloud.io/api/project_badges/measure?project=omar2535_GraphQLer&metric=security_rating" alt="security" /></a>
<!-- <a href="https://codeclimate.com/github/omar2535/GraphQLer/test_coverage" target="_blank"><img src="https://api.codeclimate.com/v1/badges/a34db44e691904955ded/test_coverage" alt="coverage" /></a> -->
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
usage: __main__.py [-h] --url URL [--path PATH] [--config CONFIG] --mode {compile,fuzz,idor,run,single} [--auth AUTH] [--proxy PROXY] [--node NODE] [--plugins-path PLUGINS_PATH] [--version]

options:
  -h, --help            show this help message and exit
  --url URL             remote host URL
  --path PATH           directory location for files to be saved-to/used-from. Defaults to graphqler-output
  --config CONFIG       configuration file for the program
  --mode {compile,fuzz,idor,run,single}
                        mode to run the program in
  --auth AUTH           authentication token Example: 'Bearer arandompat-abcdefgh'
  --proxy PROXY         proxy to use for requests (ie. http://127.0.0.1:8080)
  --node NODE           node to run (only used in single mode)
  --plugins-path PLUGINS_PATH
                        path to plugins directory
  --version             display versionn
```

Below will be the steps on how you can use this program to test your GraphQL API. The usage is split into 2 phases, **compilation** and **fuzzing**.

- **Compilation mode**:This mode is responsible for running an *introspection query* against the given API and generating the dependency graphh
- **Fuzzing mode**: This mode is responsible for traversing the dependency graph and sending test requests to the API

A third mode is also included for ease of use, called **run** mode. this mode compiles both the compilation and fuzzing mode into one single command.

A mode in development right now is known as the IDOR mode, which will look for re-used objects that are accessible using another access token.

### Compile mode

```sh
python -m graphqler --mode compile --url <URL> --path <SAVE_PATH>
```

After compiling, you can view the compiled results in the `<SAVE_PATH>/compiled`. Additionally, a graph will have been generated called `dependency_graph.png` for inspection. Any `UNKNOWNS` in the compiled `.yaml` files can be manually marked; however, if not marked the fuzzer will still run them but just without using a dependency chain.

### Fuzz mode

```sh
python -m graphqler --mode fuzz --url <URL> --path <SAVE_PATH>
```

While fuzzing, statistics related to the GraphQL API and any ongoing request counts are logged in the console. Any request return codes are written to `<SAVE_PATH>/stats.txt`. All logs during fuzzing are kept in `<SAVE_PATH>/logs/fuzzer.log`. The log file will tell you exactly which requests are sent to which endpoints, and what the response was. This can be used for further result analysis. A copy of the objects bucket can be found in `objects_bucket.pkl` as well.

### IDOR Checking mode

```sh
python -m graphqler --mode idor --url <URL> --path <SAVE_PATH>
```

The [insecure direct object reference (IDOR)](https://portswigger.net/web-security/access-control/idor) mode can be run after **compile** mode and **fuzz** mode is complete. It requires the `objects_bucket.pkl` file to already exist as it uses the objects bucket from a previous run to see if information found/created from a previous run is also reference-able in a new run.

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

Furthermore, you can implement your own plugins for custom authentication. See more in the docs.
