<p align="center">
  <img src="./docs/images/logo.png" />
  <p align="center">The <strong>only</strong> dependency-aware GraphQL API testing tool!</p>
</p>

<p align="center">
<a href="https://www.python.org/downloads/" target="_blank"><img src="https://img.shields.io/badge/python-3.11-blue" alt="python3.11"/></a>
<a href="https://codeclimate.com/github/omar2535/GraphQLer/maintainability" target="_blank"><img src="https://api.codeclimate.com/v1/badges/a34db44e691904955ded/maintainability" alt="Maintainability" /></a>
<a href="https://github.com/omar2535/GraphQLer/actions/workflows/lint.yml" target="_blank"><img src="https://github.com/omar2535/GraphQLer/actions/workflows/lint.yml/badge.svg" alt="lint" /></a>
<a href="https://github.com/omar2535/GraphQLer/actions/workflows/tests.yml" target="_blank"><img src="https://github.com/omar2535/GraphQLer/actions/workflows/tests.yml/badge.svg?branch=main" alt="tests_status" /></a>
<a href="https://sonarcloud.io/summary/new_code?id=omar2535_GraphQLer" target="_blank"><img src="https://sonarcloud.io/api/project_badges/measure?project=omar2535_GraphQLer&metric=security_rating" alt="security" /></a>
<!-- <a href="https://codeclimate.com/github/omar2535/GraphQLer/test_coverage" target="_blank"><img src="https://api.codeclimate.com/v1/badges/a34db44e691904955ded/test_coverage" alt="coverage" /></a> -->
</p>

GraphQLer is a cutting-edge tool designed to dynamically test GraphQL APIs with a focus on adaptability and comprehensive testing. It offers a range of sophisticated features that streamline the testing process and ensure robust analysis of GraphQL APIs. By leveraging intelligent tracking mechanisms, GraphQLer proficiently manages created objects and resources, effectively identifies dependencies on objects, queries, and mutations, and dynamically rectifies errors within queries based on the API's restrictions.

![Video Demo](./docs/demo.gif)

## Key features

- Dependency awareness: Run queries and mutations based on their dependencies!
- Dynamic testing: Keep track of resources created during testing
- Error correction: Try and fix requests so that the GraphQL API accepts them
- Statistics collection: Shows your results in a nice file
- Ease of use: All you need is the endpoint and *maybe* the authentication token 😁

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

### Fuzz mode

```sh
(.env) python main.py --fuzz --url <URL> --path <SAVE_PATH>
```

### Run mode

Runs both the Compile mode and Fuzz mode

```sh
(.env) python main.py --run --url <URL> --path <SAVE_PATH>
```
