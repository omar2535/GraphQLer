# Installation

!!! info "Prerequisites"

    - **Python 3.12** (GraphQLer requires `>=3.12,<3.13`)
    - **Windows users** need Microsoft C++ Build Tools (VC 14 or newer) — get them from the [Microsoft page](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

## User setup

=== "pip"

    GraphQLer is published on [PyPI](https://pypi.org/project/GraphQLer/):

    ```sh
    pip install GraphQLer
    python -m graphqler --help
    ```

    To use the [MCP server](mcp.md), install the optional extras:

    ```sh
    pip install "GraphQLer[mcp]"
    ```

=== "Docker"

    Images are published to [Docker Hub](https://hub.docker.com/r/omar2535/graphqler) and the GitHub Container Registry (`ghcr.io/omar2535/graphqler`):

    ```sh
    docker pull omar2535/graphqler:latest
    docker run --rm omar2535/graphqler --help
    ```

    The container's entrypoint is `python -m graphqler` with working directory `/app`. Mount a volume to keep the output directory:

    ```sh
    docker run --rm -v "$PWD/graphqler-output:/app/graphqler-output" \
      omar2535/graphqler --mode run --url https://example.com/graphql
    ```

## Developer setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) first.

### 1. Install OS-specific dependencies

On Ubuntu:

```sh
sudo apt-get install build-essential
```

### 2. Set up the environment

```sh
uv sync --extra mcp
source .venv/bin/activate
```

### 3. Run GraphQLer

```sh
uv run python -m graphqler --version
```

### 4. Install pre-commit hooks (optional)

```sh
pre-commit install
```

### 5. Run tests

```sh
uv run pytest tests/unit/          # unit tests
uv run pytest tests/integration/   # integration tests
uv run pytest tests/e2e/           # end-to-end tests
```

The end-to-end tests need the sample APIs in `sample-graphql-apis/` — see [Contributing](CONTRIBUTING.md#running-tests).

### 6. Preview the documentation (optional)

This site is built with [Zensical](https://zensical.org/):

```sh
uv run --only-group docs zensical serve
```
