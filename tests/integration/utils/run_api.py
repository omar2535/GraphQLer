import subprocess
import os
import requests
import time
import shutil


def run_node_project(path: str, commands: list[str], port: str) -> subprocess.Popen:
    """Runs a node project with the given commands and sets the PORT environment variable.

    Args:
        path (str): The path to the project
        commands (list[str]): The list of commands
        port (str): The port to set for the environment variable

    Returns:
        subprocess.Popen: The process object
    """
    # Set the environment variable
    env = os.environ.copy()
    env["PORT"] = port
    shell_flag = os.name == "nt"  # True no Windows, False no Linux/macOS

    # Run npm install with proper handling
    npm_cmd = shutil.which("npm")
    node_cmd = shutil.which("node")
    if npm_cmd is None:
        raise RuntimeError("npm command not found. Please ensure Node.js is installed.")
    
    try:
        subprocess.run([npm_cmd, "install"], cwd=path, check=True, env=env, shell=shell_flag)
    except subprocess.CalledProcessError as e:
        print(f"npm install failed: {e}")
        raise

    # Run each command in the list
    for command in commands:
        subprocess.run(command.split(), cwd=path, check=True, env=env, shell=shell_flag)

    # Run node server.js
    process = subprocess.Popen([node_cmd, "server.js"], cwd=path, env=env, shell=shell_flag)

    return process


def wait_for_server(url, timeout=30):
    """Wait for the server to start by continuously checking the given URL.

    Args:
        url (str): The URL to check.
        timeout (int): Maximum time to wait for the server to start in seconds.

    Returns:
        bool: True if the server is ready, False if the timeout is reached.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    return False
