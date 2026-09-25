# Vulnerability detection

During fuzzing, detectors send targeted payloads to each query and mutation — using real object IDs from the objects bucket — and inspect the responses. Every finding is recorded in `stats.txt`/`stats.json` and written to `detections/` (see [Output files](output.md#detections)).

Findings are reported as either **vulnerable** (confirmed by the response) or **potentially vulnerable** (suspicious, worth manual review).

## Detectors

### Injection

Enabled unless `SKIP_INJECTION_ATTACKS = true`.

| Detection | What it looks for |
|---|---|
| SQL Injection (SQLi) | Database error signatures after SQL payloads |
| Time-based SQL Injection (Blind SQLi) | Response delays after `pg_sleep` / `SLEEP` / `WAITFOR` payloads (`TIME_BASED_SQL_SLEEP_SECONDS`, `TIME_BASED_SQL_THRESHOLD_RATIO`) |
| NoSQL Injection (NoSQLi) | Operator injection; optional blind data extraction with `NOSQLI_BLIND_EXTRACTION = true` |
| OS Command Injection | Command output (e.g. `/etc/passwd` content) in responses |
| Path Injection | File contents returned via path traversal |
| SSRF Injection | Server-side request forgery indicators |
| Cross-Site Scripting (XSS) | Reflected script payloads |

### Miscellaneous

Enabled unless `SKIP_MISC_ATTACKS = true`.

| Detection | What it looks for |
|---|---|
| Query deny bypass | A query rejected with HTTP 400 succeeds when sent under an alias |
| DoS: Field Duplication | Server accepts heavily duplicated fields |
| DoS: Circular Fragment | Server accepts circular fragment definitions |
| DoS: Resource Exhaustion | No upper bound on pagination-like inputs (`first`, `limit`, `count`, …) |

Additional DoS payloads (aliasing, batching, deep recursion) are **skipped by default**; set `SKIP_DOS_ATTACKS = false` to send them. Only do so against services you can afford to take down.

### Enumeration

Disabled by default because they send many requests per node; enable with `SKIP_ENUMERATION_ATTACKS = false`.

| Detection | What it looks for |
|---|---|
| Field Charset Enumeration (Blind Data Extraction) | Response differences when fuzzing string fields character by character (`FIELD_CHARSET`, `MAX_CHARSET_FUZZ_FIELDS`) |
| IDOR / ID Enumeration | Data returned for sequential integer IDs `1..ID_ENUMERATION_COUNT` |

### API-level

Run once per API.

| Detection | What it looks for |
|---|---|
| Introspection Enabled | The schema is exposed through introspection |
| Field Suggestions Enabled | "Did you mean …" suggestions leak field names |

### Chain-based

| Detection | What it looks for |
|---|---|
| IDOR | A second user can read or modify objects created by the first |
| Use-after-delete (UAF) | A deleted object can still be accessed |

See [IDOR & UAF chains](idor.md).

## Turning detections off

```sh
python -m graphqler --mode fuzz --url <URL> --no-detections
```

`--no-detections` sets every `SKIP_*_ATTACKS` flag, leaving only coverage-oriented fuzzing.
