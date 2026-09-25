# Configuration

GraphQLer reads a TOML file passed with `--config`. Without it, `<PATH>/config.toml` is used if present, otherwise one is generated there. CLI flags override the file, and the resolved configuration is written back to `<PATH>/config.toml` on every run.

## Common settings

| Variable | Description | Type | Default |
|---|---|---|---|
| `MAX_LEVENSHTEIN_THRESHOLD` | Levenshtein distance for matching object names to ID inputs | Integer | `20` |
| `MAX_OBJECT_CYCLES` | Max times the same object is materialised in one query/mutation | Integer | `5` |
| `MAX_OUTPUT_SELECTOR_DEPTH` | Max depth of output selections (guards against recursive types) | Integer | `5` |
| `USE_OBJECTS_BUCKET` | Store returned objects for later requests | Boolean | `true` |
| `USE_DEPENDENCY_GRAPH` | Order requests using the dependency graph | Boolean | `true` |
| `ALLOW_DELETION_OF_OBJECTS` | Remove objects from the bucket after a successful DELETE | Boolean | `false` |
| `MAX_FUZZING_ITERATIONS` | Number of sweeps through all chains | Integer | `1` |
| `MAX_TIME` | Maximum run time in seconds | Integer | `3600` |
| `REQUEST_TIMEOUT` | Per-request timeout in seconds | Integer | `120` |
| `TIME_BETWEEN_REQUESTS` | Minimum delay between requests in seconds | Float | `0.001` |
| `DEBUG` | Debug mode | Boolean | `false` |
| `SKIP_MAXIMAL_PAYLOADS` | Skip payloads that request every possible output field | Boolean | `false` |
| `SKIP_DOS_ATTACKS` | Skip DoS detections (on by default to avoid taking the service down) | Boolean | `true` |
| `SKIP_INJECTION_ATTACKS` | Skip injection detections | Boolean | `false` |
| `SKIP_MISC_ATTACKS` | Skip miscellaneous detections | Boolean | `false` |
| `SKIP_ENUMERATION_ATTACKS` | Skip field-charset and ID enumeration detections (many requests per node) | Boolean | `true` |
| `SKIP_SUBSCRIPTIONS` | Skip subscription fuzzing (`--subscriptions` enables it) | Boolean | `true` |
| `SUBSCRIPTION_PROTOCOL` | `graphql-transport-ws` or legacy `subscriptions-transport-ws` | String | `graphql-transport-ws` |
| `SKIP_NODES` | Query/mutation names to skip | List | `[]` |
| `DISABLE_MUTATIONS` | Only generate and run Query chains (`--disable-mutations`) | Boolean | `false` |
| `SAVE_ENDPOINT_RESULTS` | Write per-endpoint result files | Boolean | `true` |
| `IDOR_SECONDARY_AUTH` | Secondary (attacker) token for [IDOR chains](idor.md) | String | unset |
| `SKIP_IDOR_CHAIN_FUZZING` | Disable the IDOR chain phase | Boolean | `false` |
| `SKIP_UAF_CHAIN_FUZZING` | Disable the use-after-delete chain phase | Boolean | `false` |
| `[CUSTOM_HEADERS]` | Headers sent with every request | Table | `Accept = "application/json"` |

LLM settings are described in [LLM features](llm.md).

## Custom headers

```toml
[CUSTOM_HEADERS]
Accept = "application/json"
Cookie = "session=abc123"
X-Api-Key = "secret"
```

## Authentication profiles

`--auth` sets the primary `Authorization` header. Named profiles are passed as `profile=token`:

```sh
python -m graphqler --mode run --url <URL> \
  --auth 'primary=Bearer <VICTIM_TOKEN>' \
  --auth 'secondary=Bearer <ATTACKER_TOKEN>'
```

`primary` is the default identity; `secondary` is equivalent to `--idor-auth` and enables [IDOR chains](idor.md).

## Example configuration

An annotated example shipped with GraphQLer (`graphqler/examples/config.toml`). Defaults in the table above come from `graphqler/config.py`.

```toml
--8<-- "graphqler/examples/config.toml"
```
