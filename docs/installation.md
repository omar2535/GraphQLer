# Installation guide

**Pre-requisites:**

- **Windows users** will need to have VCC14 or higher. Get it at the [microsoft page](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- Have **python 3.12**

## User setup guide

You can install GraphQLer via pip:

```sh
pip install GraphQLer
```

and use it like so:

```sh
python -m graphqler --help
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
