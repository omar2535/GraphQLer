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

Firstly, it is recommended to do everythiong in a pyenv and virtual environment. Links are provided below, but not necessary:

- [pyenv](https://github.com/pyenv/pyenv) - Manages your python version for you
- [venv](https://docs.python.org/3/library/venv.html) - Manages dependencies in a virtual environment

Next, we'll install the package manager for this project.

### Using uv (Recommended)

Install [here](https://docs.astral.sh/uv/getting-started/installation/)

**Setting up the environment:**

```sh
# Creating the virtual environment & Install dependencies
uv sync
source .venv/bin/activate
```

**Running GraphQLer:**

```sh
uv run graphqler --version
```

**Setting up pre-commit hooks (optional):**

```sh
(.env) pre-commit install
```
