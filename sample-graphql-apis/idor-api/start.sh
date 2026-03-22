#!/usr/bin/env bash
# start.sh — install deps (if needed) and start the IDOR test API on port 8000

set -e
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "[*] Syncing dependencies with uv..."
uv sync -q

echo ""
echo "=== IDOR Test API ==="
echo "Tokens:"
echo "  Alice (victim)  : Bearer alice_token_abc123"
echo "  Bob   (attacker): Bearer bob_token_xyz789"
echo ""
echo "GraphQL endpoint: http://localhost:8000/graphql"
echo ""
uv run python app.py
