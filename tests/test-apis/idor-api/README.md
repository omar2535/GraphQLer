# IDOR Test API

A deliberately vulnerable GraphQL API for testing GraphQLer's IDOR detection.

## Quick start

```bash
cd tests/test-apis/idor-api
./start.sh
# API is live at http://localhost:8000/graphql
```

Or manually:

```bash
cd tests/test-apis/idor-api
uv sync
uv run python app.py
```

## Hard-coded tokens

| User | Token | Role |
|------|-------|------|
| Alice | `Bearer alice_token_abc123` | Victim (primary) |
| Bob | `Bearer bob_token_xyz789` | Attacker (secondary) |

## IDOR vulnerabilities

| Operation | Type | Issue |
|-----------|------|-------|
| `getNote(id)` | Query | Returns any note without ownership check |
| `updateNote(id, ...)` | Mutation | Updates any note without ownership check |
| `deleteNote(id)` | Mutation | Deletes any note without ownership check |
| `getOrder(id)` | Query | Returns any order without ownership check |
| `deleteOrder(id)` | Mutation | Deletes any order without ownership check |

Correctly secured: `myNotes`, `myOrders`.

## Testing with GraphQLer

```bash
# 1. Compile the schema
graphqler --mode compile \
    --url http://localhost:8000/graphql \
    --path ./output \
    --token "Bearer alice_token_abc123" \
    --idor-auth "Bearer bob_token_xyz789"

# 2. Fuzz (IDOR phase runs automatically)
graphqler --mode fuzz \
    --url http://localhost:8000/graphql \
    --path ./output \
    --token "Bearer alice_token_abc123" \
    --idor-auth "Bearer bob_token_xyz789"

# Or compile + fuzz in one step
graphqler --mode run \
    --url http://localhost:8000/graphql \
    --path ./output \
    --token "Bearer alice_token_abc123" \
    --idor-auth "Bearer bob_token_xyz789"
```

Expected findings: `IDOR_CHAIN` vulnerability detected on `getNote`, `getOrder`.

## Manual verification

```graphql
# Step 1: Alice creates a note (use Authorization: Bearer alice_token_abc123)
mutation {
  createNote(title: "Alice's secret", content: "Private data") {
    id
    owner
  }
}

# Step 2: Bob reads Alice's note using the returned ID (use Authorization: Bearer bob_token_xyz789)
# This should fail but DOESN'T — that's the IDOR vulnerability
query {
  getNote(id: "<alice-note-id>") {
    title
    content
    owner
  }
}
```
