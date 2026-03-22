"""
IDOR Test API
=============
A deliberately vulnerable GraphQL API used to validate the GraphQLer IDOR fuzzer.

Intentional vulnerabilities
----------------------------
* getNote(id)       -- returns any note by ID regardless of who owns it  (IDOR)
* updateNote(...)   -- updates any note by ID regardless of ownership     (IDOR)
* deleteNote(id)    -- deletes any note by ID regardless of ownership     (IDOR)
* getOrder(id)      -- returns any order by ID regardless of ownership    (IDOR)
* deleteOrder(id)   -- deletes any order by ID regardless of ownership    (IDOR)

Correctly secured endpoints
----------------------------
* myNotes           -- only returns notes owned by the authenticated user
* myOrders          -- only returns orders owned by the authenticated user

Hard-coded tokens
-----------------
  Alice (victim)  : Bearer alice_token_abc123
  Bob   (attacker): Bearer bob_token_xyz789

Usage with GraphQLer
--------------------
  graphqler --mode run \
      --url http://localhost:8000/graphql \
      --path ./graphqler-output \
      --token "Bearer alice_token_abc123" \
      --idor-auth "Bearer bob_token_xyz789"
"""

from __future__ import annotations

import uuid
from typing import Optional

import graphene
from flask import Flask, request, jsonify


# ---------------------------------------------------------------------------
# In-memory data store
# ---------------------------------------------------------------------------

TOKENS: dict[str, str] = {
    "Bearer alice_token_abc123": "alice",
    "Bearer bob_token_xyz789": "bob",
}

notes_db: dict[str, dict] = {}
orders_db: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def get_current_user() -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    return TOKENS.get(auth)


def require_auth() -> str:
    user = get_current_user()
    if not user:
        raise Exception("Authentication required. Provide a valid Bearer token.")
    return user


# ---------------------------------------------------------------------------
# GraphQL types
# ---------------------------------------------------------------------------

class NoteType(graphene.ObjectType):
    class Meta:
        name = "Note"

    id = graphene.ID(required=True)
    title = graphene.String(required=True)
    content = graphene.String(required=True)
    owner = graphene.String(required=True)


class OrderType(graphene.ObjectType):
    class Meta:
        name = "Order"

    id = graphene.ID(required=True)
    item = graphene.String(required=True)
    quantity = graphene.Int(required=True)
    owner = graphene.String(required=True)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

class Query(graphene.ObjectType):
    get_note = graphene.Field(
        NoteType,
        id=graphene.ID(required=True),
        description="IDOR vulnerability: returns any note without ownership check",
    )
    my_notes = graphene.List(
        graphene.NonNull(NoteType),
        description="Secure: returns only the caller's own notes",
    )
    get_order = graphene.Field(
        OrderType,
        id=graphene.ID(required=True),
        description="IDOR vulnerability: returns any order without ownership check",
    )
    my_orders = graphene.List(
        graphene.NonNull(OrderType),
        description="Secure: returns only the caller's own orders",
    )

    def resolve_get_note(self, info, id):
        require_auth()
        row = notes_db.get(str(id))
        if row is None:
            return None
        return NoteType(id=id, title=row["title"], content=row["content"], owner=row["owner"])

    def resolve_my_notes(self, info):
        user = require_auth()
        return [
            NoteType(id=nid, title=r["title"], content=r["content"], owner=r["owner"])
            for nid, r in notes_db.items()
            if r["owner"] == user
        ]

    def resolve_get_order(self, info, id):
        require_auth()
        row = orders_db.get(str(id))
        if row is None:
            return None
        return OrderType(id=id, item=row["item"], quantity=row["quantity"], owner=row["owner"])

    def resolve_my_orders(self, info):
        user = require_auth()
        return [
            OrderType(id=oid, item=r["item"], quantity=r["quantity"], owner=r["owner"])
            for oid, r in orders_db.items()
            if r["owner"] == user
        ]


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------

class CreateNote(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        content = graphene.String(required=True)

    Output = NoteType

    def mutate(self, info, title, content):
        user = require_auth()
        nid = str(uuid.uuid4())
        notes_db[nid] = {"owner": user, "title": title, "content": content}
        return NoteType(id=nid, title=title, content=content, owner=user)


class UpdateNote(graphene.Mutation):
    """IDOR: updates any note without ownership check."""

    class Arguments:
        id = graphene.ID(required=True)
        title = graphene.String()
        content = graphene.String()

    Output = NoteType

    def mutate(self, info, id, title=None, content=None):
        require_auth()
        row = notes_db.get(str(id))
        if row is None:
            return None
        if title is not None:
            row["title"] = title
        if content is not None:
            row["content"] = content
        return NoteType(id=id, title=row["title"], content=row["content"], owner=row["owner"])


class DeleteNote(graphene.Mutation):
    """IDOR: deletes any note without ownership check."""

    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean(required=True)

    def mutate(self, info, id):
        require_auth()
        if str(id) in notes_db:
            del notes_db[str(id)]
            return DeleteNote(ok=True)
        return DeleteNote(ok=False)


class CreateOrder(graphene.Mutation):
    class Arguments:
        item = graphene.String(required=True)
        quantity = graphene.Int(required=True)

    Output = OrderType

    def mutate(self, info, item, quantity):
        user = require_auth()
        oid = str(uuid.uuid4())
        orders_db[oid] = {"owner": user, "item": item, "quantity": quantity}
        return OrderType(id=oid, item=item, quantity=quantity, owner=user)


class DeleteOrder(graphene.Mutation):
    """IDOR: deletes any order without ownership check."""

    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean(required=True)

    def mutate(self, info, id):
        require_auth()
        if str(id) in orders_db:
            del orders_db[str(id)]
            return DeleteOrder(ok=True)
        return DeleteOrder(ok=False)


class Mutation(graphene.ObjectType):
    create_note = CreateNote.Field()
    update_note = UpdateNote.Field()
    delete_note = DeleteNote.Field()
    create_order = CreateOrder.Field()
    delete_order = DeleteOrder.Field()


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

schema = graphene.Schema(query=Query, mutation=Mutation)
app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "description": "Intentionally vulnerable GraphQL API for IDOR testing",
        "graphql_endpoint": "/graphql",
        "tokens": {
            "alice (victim)": "Bearer alice_token_abc123",
            "bob (attacker)": "Bearer bob_token_xyz789",
        },
        "idor_vulnerable_operations": ["getNote", "updateNote", "deleteNote", "getOrder", "deleteOrder"],
        "secure_operations": ["myNotes", "myOrders"],
    })


@app.route("/graphql", methods=["POST"])
def graphql_view():
    data = request.get_json(force=True)
    query = data.get("query", "")
    variables = data.get("variables")
    operation_name = data.get("operationName")

    result = schema.execute(
        query,
        variables=variables,
        operation_name=operation_name,
        context_value={"request": request},
    )

    response: dict = {}
    if result.data:
        response["data"] = result.data
    if result.errors:
        response["errors"] = [{"message": str(e)} for e in result.errors]

    status = 400 if (result.errors and not result.data) else 200
    return jsonify(response), status


@app.route("/graphql", methods=["GET"])
def graphql_introspect():
    """Serve a minimal introspection response for schema discovery."""
    result = schema.execute("{ __schema { queryType { name } mutationType { name } } }")
    return jsonify({"data": result.data})


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    print("=== IDOR Test API ===")
    print("Tokens:")
    print("  Alice (victim)  : Bearer alice_token_abc123")
    print("  Bob   (attacker): Bearer bob_token_xyz789")
    print("")
    print(f"GraphQL endpoint: http://localhost:{port}/graphql")
    print("")
    app.run(host="0.0.0.0", port=port, debug=False)
