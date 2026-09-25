# IDOR & UAF chains

Some vulnerabilities only appear across several requests. GraphQLer derives multi-step **chains** from the dependency graph during compilation and replays them during fuzzing.

## IDOR

[Insecure direct object reference (IDOR)](https://portswigger.net/web-security/access-control/idor) detection uses two identities:

- **primary** — the victim, set with `--auth`
- **secondary** — the attacker, set with `--idor-auth` (or `--auth 'secondary=…'`, or `IDOR_SECONDARY_AUTH` in the config)

```sh
python -m graphqler --mode compile --url <URL> --path <SAVE_PATH> \
  --auth 'Bearer <VICTIM_TOKEN>' --idor-auth 'Bearer <ATTACKER_TOKEN>'
python -m graphqler --mode fuzz --url <URL> --path <SAVE_PATH>
```

### How it works

1. **Compile.** Endpoints that create or expose user-scoped objects are identified and turned into chains saved to `compiled/chains/idor.yml`. Setup steps run as `primary`; test steps run as `secondary`.
2. **Fuzz.** The primary profile creates or retrieves the object, then the secondary profile tries to access it. Any data returned to the secondary profile is flagged and written to `detections/IDOR_CHAIN/<node>/`.
3. **Re-test** (optional). `--mode idor` replays only the IDOR chains.

### Candidate scoring

Chains are scored by a heuristic classifier (0.0–1.0):

| Signal | Score |
|---|---|
| CREATE mutation output type matches the test node's input type | +0.5 |
| Test node name contains private-resource keywords (`user`, `order`, `profile`, …) | +0.3 |
| Test node accepts an `ID`/`Int` parameter | +0.2 |
| Test node name contains public-resource keywords (`list`, `public`, `catalog`, …) | −0.2 |

With `USE_LLM = true` and `IDOR_USE_LLM_FALLBACK = true`, chains scoring below `IDOR_HEURISTIC_CONFIDENCE_THRESHOLD` (default `0.5`) are sent to an [LLM classifier](llm.md).

Disable the phase with `SKIP_IDOR_CHAIN_FUZZING = true`.

## Use-after-delete (UAF)

UAF chains look for a `CREATE → … → DELETE → … → ACCESS` pattern in the regular chains and are saved to `compiled/chains/uaf.yml`. All steps run with the primary token; steps after the delete are labelled `post_delete`. If a `post_delete` step still returns data, the API is serving a resource that should no longer exist and a finding is recorded.

No second identity is needed. Related settings:

| Variable | Default |
|---|---|
| `SKIP_UAF_CHAIN_FUZZING` | `false` |
| `UAF_HEURISTIC_CONFIDENCE_THRESHOLD` | `0.5` |
| `UAF_USE_LLM_FALLBACK` | `false` |
