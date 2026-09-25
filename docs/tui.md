# Interactive TUI

Run GraphQLer with no arguments to open the interactive terminal UI:

```sh
python -m graphqler
```

The TUI provides every workflow without memorising flags:

| Screen | What it does |
|---|---|
| **Compile** | Run introspection and generate dependency chains |
| **Fuzz** | Execute chains against the target API |
| **Run** | Compile + fuzz in one step |
| **IDOR** | Replay chains with a secondary auth token to detect IDOR |
| **Chain Explorer** | Browse compiled chains and execute them individually |
| **Query Editor** | Write and send free-form GraphQL requests |
| **Configure** | Set the endpoint URL, auth tokens, proxy, timeouts and LLM settings — saved to `config.toml` |
| **Browse Output** | Browse and inspect all files in the output directory |

An animated splash screen is shown on the first launch each day. Press any key to skip it.

!!! note

    Inside the TUI the fuzzer runs in threads rather than subprocesses so logs and progress can be streamed into the interface.
