# Installation guide

**Pre-requisites:**

- **Windows users** will need to have VCC14 or higher. Get it at the [microsoft page](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- Make sure to have **python 3.12**

## Using Poetry (Recommended)

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

## Using PIP

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
