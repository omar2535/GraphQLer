# 🙂 Installation guide

**Pre-requisites:**

- **Windows users** will need to have VCC14 or higher. Get it at the [microsoft page](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- Have **python 3.12**

## 😀 User setup guide

### Pip

You can install GraphQLer via pip. The Pypi listing: [Pypi](https://pypi.org/project/GraphQLer/)

```sh
pip install GraphQLer
```

and use it like so:

```sh
python -m graphqler --help
```

### Docker

The dockerhub repository: [Dockerhub](https://hub.docker.com/repository/docker/omar2535/graphqler/general)

```sh
docker pull omar2535/graphqler:latest
```

and you can run it like so:

```sh
docker run --rm omar2535/graphqler --help
```

## 🤓 Developer setup guide

Follow these steps to get set up as a developer. Firstly, setup uv by following [these steps](https://docs.astral.sh/uv/getting-started/installation/)

### 1. Install OS specific dependencies

For ubuntu

```sh
sudo apt-get install build-essential
```


### 2. Setting up the environment

```sh
# Creating the virtual environment & Install dependencies
uv sync
source .venv/bin/activate
```

### 3. Running GraphQLer

```sh
uv run graphqler --version
```

### 4. Setting up pre-commit hooks (optional)

```sh
(.env) pre-commit install
```

### 5. Running tests

**Unit tests:**

```sh
uv run pytest tests/unit/
```

**Integration tests:**

```sh
uv run pytest tests/integration/
```
