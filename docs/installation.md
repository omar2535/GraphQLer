# Installation guide

**Pre-requisites:**

- **Windows users** will need to have VCC14 or higher. Get it at the [microsoft page](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- Make sure to have **python 3.11** or higher already installed

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

everything should work after that!
