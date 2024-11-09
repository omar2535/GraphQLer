# Contributing

Constributing is simple:

1. Fork the repository
2. Make your changes
3. Open a pull request
4. Get the pull request reviewed
5. Merge into main

## Development

The development environment follows the same steps as the installation guide, so we refer to it there.
The only main point is to use the **poetry** installation instead of the docker installation.

Here is a sample vscode debug configuration:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: GraphQLer",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/graphqler",
            "args": [
                "--url", "https://<endpoint>/graphql",
                "--path", "output-test/<my-test>",
                "--config", "output-test/<my-test>.toml",
                "--mode", "run"
            ],
            "console": "integratedTerminal",
            "justMyCode": true
        }
    ]
}
```

### Building the sphinx-docs

```sh
sphinx-apidoc -o sphinx/docs graphqler
cd sphinx && make html
```


## Running tests

To run integration tests, you will have to first set up the sample APIs by running the following:

**Food delivery API:**

```sh
cd tests/test-apis/food-delivery-api
npm install
node dbinitializer.js
node server.js
```
