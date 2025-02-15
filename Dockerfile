# Use a base image with Python 3.12 installed
FROM python:3.12

# Install uv
## The installer requires curl (and certificates) to download the release archive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

## Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

## Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

## Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Install graphqler
# Set the working directory inside the container
WORKDIR /app

# Copy the uv.lock and pyproject.toml files to the working directory
COPY uv.lock pyproject.toml ./

# Copy the rest of the application code to the working directory
COPY . .

# Install project dependencies using Poetry
RUN uv sync

# Use ENTRYPOINT to make the script receive arguments
ENTRYPOINT ["uv", "run", "python", "-m", "graphqler"]
