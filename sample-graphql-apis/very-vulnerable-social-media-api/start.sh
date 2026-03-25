#!/usr/bin/env bash
# start.sh — install deps and start the Very Vulnerable Social Media API

set -e
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "[*] Syncing dependencies with uv..."
uv sync -q

echo ""
echo "=== Very Vulnerable GraphQL API — Social Media Edition ==="
echo "Tokens:"
echo "  Alice : Bearer alice_social_token"
echo ""
echo "UAF-vulnerable endpoint: getPost(id)  — still returns deleted posts!"
echo ""
echo "GraphQL endpoint: http://localhost:8001/graphql"
echo ""
uv run python app.py
