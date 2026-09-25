---
title: GraphQLer
hide:
  - navigation
---

<p align="center">
  <img src="images/logo.png" alt="GraphQLer" width="360" />
</p>

<p align="center"><strong>The dependency-aware GraphQL API security testing tool</strong></p>

<p align="center">
<a href="https://pypi.org/project/GraphQLer/"><img src="https://img.shields.io/pypi/v/GraphQLer?style=flat&logo=pypi" alt="PyPI"/></a>
<a href="https://hub.docker.com/r/omar2535/graphqler"><img src="https://img.shields.io/docker/image-size/omar2535/graphqler/latest?style=flat&logo=docker" alt="Docker"/></a>
<a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12-blue" alt="python3.12"/></a>
<a href="https://arxiv.org/pdf/2504.13358"><img src="https://img.shields.io/badge/cs.CR-arXiv%3A2504.13358-B31B1B.svg" alt="arXiv"/></a>
<a href="https://github.com/omar2535/GraphQLer/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License"/></a>
</p>

GraphQLer dynamically tests GraphQL APIs. It reads the schema through introspection, works out which queries and mutations depend on which objects, and then executes requests in dependency order — so a `createPost` runs before the `updatePost` that needs its ID. The objects returned along the way are reused in later requests and fed to a suite of security detectors.

[Get started :material-arrow-right:](installation.md){ .md-button .md-button--primary }
[View on GitHub :fontawesome-brands-github:](https://github.com/omar2535/GraphQLer){ .md-button }

## Key features

<div class="grid cards" markdown>

-   :material-file-tree:{ .lg .middle } **Dependency awareness**

    ---

    Builds a dependency graph from the schema and runs queries and mutations in their natural order.

    [:octicons-arrow-right-24: Modes](modes.md)

-   :material-code-braces:{ .lg .middle } **Request generation**

    ---

    Generates valid queries and mutations, including fragments, unions, interfaces and enums.

-   :material-database-search:{ .lg .middle } **Resource tracking**

    ---

    An *objects bucket* keeps every object seen in responses for reuse and reconnaissance.

    [:octicons-arrow-right-24: Output files](output.md)

-   :material-shield-bug:{ .lg .middle } **Vulnerability detection**

    ---

    Injection, DoS, information disclosure, IDOR and use-after-delete checks, each with a reproducible request log.

    [:octicons-arrow-right-24: Detectors](detectors.md)

-   :material-robot:{ .lg .middle } **Optional LLM assistance**

    ---

    Infer dependencies, classify IDOR/UAF chains and write a vulnerability report with any `litellm` model.

    [:octicons-arrow-right-24: LLM features](llm.md)

-   :material-console:{ .lg .middle } **CLI, TUI and MCP**

    ---

    Drive it from the command line, an interactive terminal UI, Python, or an AI assistant over MCP.

    [:octicons-arrow-right-24: Interactive TUI](tui.md)

</div>

## At a glance

```sh
pip install GraphQLer
python -m graphqler --mode run --url https://example.com/graphql --auth 'Bearer <TOKEN>'
```

GraphQLer works in two phases connected by files on disk:

```mermaid
flowchart LR
    API[(GraphQL API)] -->|introspection| C[Compile]
    C -->|schema YAML, dependency graph, chains| D[(Output directory)]
    D --> F[Fuzz]
    F -->|requests| API
    F -->|stats, logs, detections| D
```

1. **Compile** — introspect the schema, resolve dependencies, draw the dependency graph and generate fuzzing chains.
2. **Fuzz** — execute the chains, track objects, run detectors and record results.

## Demo

<video src="https://github.com/user-attachments/assets/0c0595a7-d0d9-4554-998a-98d6ebd1fbc2" controls width="100%"></video>

## Citation

If you use GraphQLer in research, please cite the [paper on arXiv](https://arxiv.org/abs/2504.13358) or the software via [`CITATION.cff`](https://github.com/omar2535/GraphQLer/blob/main/CITATION.cff).
