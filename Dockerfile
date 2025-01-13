# Use a base image with Python 3.12 installed
FROM python:3.12

# Set the working directory inside the container
WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy the poetry.lock and pyproject.toml files to the working directory
COPY poetry.lock pyproject.toml ./

# Copy the rest of the application code to the working directory
COPY . .

# Install project dependencies using Poetry
RUN poetry install

# Use ENTRYPOINT to make the script receive arguments
ENTRYPOINT ["poetry", "run", "python", "-m", "graphqler"]
