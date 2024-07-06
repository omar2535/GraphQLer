# Installation guide

**Pre-requisites:**

- **Windows users** will need to have VCC14 or higher. Get it at the [microsoft page](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- Have **python 3.12**

## User setup guide

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

## Developer setup guide

Firstly, it is recommended to do everythiong in a pyenv and virtual environment. Links are provided below, but not necessary:

- [pyenv](https://github.com/pyenv/pyenv) - Manages your python version for you
- [venv](https://docs.python.org/3/library/venv.html) - Manages dependencies in a virtual environment

### Using Poetry (Recommended)

Install poetry [here](https://python-poetry.org/docs/)

**Setting up the environment:**

```sh
# Creating the virtual environment
python3 -m venv .venv
```

**Installing dependencies:**

```sh
poetry shell
poetry install
```

### Using requirements.txt

**Setting up the environment:**

```sh
# Creating the virtual environment
python3 -m venv .venv

# Activating the virtual environment
source .env/bin/activate
```

**Installing dependencies:**

```sh
(.env) pip install -r requirements.txt
```

**Setting up pre-commit hooks (optional):**

```sh
(.env) pre-commit install
```
