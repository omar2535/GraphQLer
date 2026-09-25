# LLM features

LLM assistance is opt-in. GraphQLer uses [litellm](https://docs.litellm.ai/docs/providers), so any supported provider works — hosted or local.

## What the LLM does

| Phase | Uses |
|---|---|
| Compilation | Infers dependencies the name-matching resolver misses (e.g. a `userEmail` string that references `User`, or unconventional mutation verbs like `provision`/`wipe`); classifies low-confidence IDOR/UAF chains |
| Fuzzing | Payload generation, error-driven request retries, endpoint classification and the optional vulnerability report |

Disable either phase with `--no-llm-compilation` or `--no-llm-fuzzing`.

## Examples

=== "Ollama (local)"

    ```sh
    python -m graphqler --mode run --url http://localhost:4000/graphql \
      --use-llm --llm-model ollama/qwen3.5:9b --llm-base-url http://localhost:11434
    ```

=== "OpenAI"

    ```sh
    export OPENAI_API_KEY=sk-...
    python -m graphqler --mode run --url <URL> --use-llm --llm-model gpt-4o-mini
    ```

=== "Anthropic"

    ```sh
    export ANTHROPIC_API_KEY=sk-ant-...
    python -m graphqler --mode run --url <URL> \
      --use-llm --llm-model anthropic/claude-3-5-haiku-20241022
    ```

=== "LiteLLM proxy"

    ```sh
    python -m graphqler --mode run --url <URL> \
      --use-llm --llm-model openai/my-model --llm-base-url http://my-proxy:4000
    ```

Add `--llm-report` to write a Markdown vulnerability report to `<PATH>/report.md` after fuzzing.

## Configuration

| Variable | Description | Default |
|---|---|---|
| `USE_LLM` | Master toggle (`--use-llm`) | `false` |
| `LLM_USE_FOR_COMPILATION` | Use the LLM during compilation | `true` |
| `LLM_USE_FOR_FUZZING` | Use the LLM during fuzzing | `true` |
| `LLM_MODEL` | litellm model string | `gpt-4o-mini` |
| `LLM_API_KEY` | API key; falls back to provider env vars | `""` |
| `LLM_BASE_URL` | Custom endpoint (Ollama, proxies) | `""` |
| `LLM_MAX_RETRIES` | Retries when the LLM returns non-JSON | `2` |
| `LLM_RESOLVER_FALLBACK_TO_ID` | Fall back to the classic resolver if the LLM call fails | `true` |
| `LLM_RESOLVER_SAVE_COMPARISON` | Save `eval/resolver_comparison.json` (LLM vs classic) | `true` |
| `LLM_ENABLE_REPORTER` | Generate the report (`--llm-report`) | `false` |
| `IDOR_USE_LLM_FALLBACK` / `UAF_USE_LLM_FALLBACK` | Send low-confidence chains to the LLM classifier | `false` |
