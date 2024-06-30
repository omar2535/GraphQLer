<p align="center">
  <img src="./docs/images/logo.png" />
  <p align="center">The <strong>only</strong> dependency-aware GraphQL API testing tool!</p>
</p>

<p align="center">
<a href="https://www.python.org/downloads/" target="_blank"><img src="https://img.shields.io/badge/python-3.12-blue" alt="python3.12"/></a>
<a href="https://codeclimate.com/github/omar2535/GraphQLer/maintainability" target="_blank"><img src="https://api.codeclimate.com/v1/badges/a34db44e691904955ded/maintainability" alt="Maintainability" /></a>
<a href="https://github.com/omar2535/GraphQLer/actions/workflows/lint.yml" target="_blank"><img src="https://github.com/omar2535/GraphQLer/actions/workflows/lint.yml/badge.svg" alt="lint" /></a>
<a href="https://github.com/omar2535/GraphQLer/actions/workflows/tests.yml" target="_blank"><img src="https://github.com/omar2535/GraphQLer/actions/workflows/tests.yml/badge.svg?branch=main" alt="tests_status" /></a>
<a href="https://sonarcloud.io/summary/new_code?id=omar2535_GraphQLer" target="_blank"><img src="https://sonarcloud.io/api/project_badges/measure?project=omar2535_GraphQLer&metric=security_rating" alt="security" /></a>
<!-- <a href="https://codeclimate.com/github/omar2535/GraphQLer/test_coverage" target="_blank"><img src="https://api.codeclimate.com/v1/badges/a34db44e691904955ded/test_coverage" alt="coverage" /></a> -->
</p>

GraphQLer is a cutting-edge tool designed to dynamically test GraphQL APIs with a focus on adaptability. It offers a range of sophisticated features that streamline the testing process and ensure robust analysis of GraphQL APIs. GraphQLer proficiently manages created objects and resources, effectively identifies dependencies on objects, queries, and mutations, and dynamically rectifies errors within queries based on the API's restrictions. GraphQLer has been used to find many bugs in production-grade GraphQL APIs!

![Video Demo](./docs/demo.gif)

## Key features

- Dependency awareness: Run queries and mutations based on their dependencies!
- Dynamic testing: Keep track of resources created during testing
- Error correction: Try and fix requests so that the GraphQL API accepts them
- Statistics collection: Shows your results in a nice file
- Ease of use: All you need is the endpoint and *maybe* the authentication token 🙂

## Getting started

To begin using GraphQLer, check out the [installation guide](./docs/installation.md).

## Usage

```sh
❯ python3 main.py --help
usage: main.py [-h] [--compile] [--fuzz] [--run] --path PATH [--auth AUTH] --url URL

options:
  -h, --help   show this help message and exit
  --compile    runs on compile mode
  --fuzz       runs on fuzzing mode
  --idor       run on IDOR checking mode
  --run        run both the compiler and fuzzer (equivalent of running --compile then running --fuzz)
  --path PATH  directory location for saved files and files to be used from
  --auth AUTH  authentication token Example: 'Bearer arandompat-abcdefgh'
  --url URL    remote host URL
```

Below will be the steps on how you can use this program to test your GraphQL API. The usage is split into 2 phases, **compilation** and **fuzzing**.

- **Compilation mode**:This mode is responsible for running an *introspection query* against the given API and generating the dependency graphh
- **Fuzzing mode**: This mode is responsible for traversing the dependency graph and sending test requests to the API

A third mode is also included for ease of use, called **run** mode. this mode compiles both the compilation and fuzzing mode into one single command.

### Compile mode

```sh
(.env) python main.py --compile --url <URL> --path <SAVE_PATH>
```

After compiling, you can view the compiled results in the `<SAVE_PATH>/compiled`. Additionally, a graph will have been generated called `dependency_graph.png` for inspection. Any `UNKNOWNS` in the compiled `.yaml` files can be manually marked; however, if not marked the fuzzer will still run them but just without using a dependency chain.

### Fuzz mode

```sh
(.env) python main.py --fuzz --url <URL> --path <SAVE_PATH>
```

While fuzzing, statistics related to the GraphQL API and any ongoing request counts are logged in the console. Any request return codes are written to `<SAVE_PATH>/stats.txt`. All logs during fuzzing are kept in `<SAVE_PATH>/logs/fuzzer.log`. The log file will tell you exactly which requests are sent to which endpoints, and what the response was. This can be used for further result analysis. A copy of the objects bucket can be found in `objects_bucket.pkl` as well.

### IDOR Checking mode

```sh
(.env) python main.py --idor --url <URL> --path <SAVE_PATH>
```

The [insecure direct object reference (IDOR)](https://portswigger.net/web-security/access-control/idor) mode can be run after **compile** mode and **fuzz** mode is complete. It requires the `objects_bucket.pkl` file to already exist as it uses the objects bucket from a previous run to see if information found/created from a previous run is also reference-able in a new run.

### Run mode

Runs both the Compile mode and Fuzz mode

```sh
(.env) python main.py --run --url <URL> --path <SAVE_PATH>
```

## Advanced features

There are also varaibles that can be modified in the `constants.py` file. These correspond to specific features implemented in GraphQLer, and can be tuned to your liking.

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
