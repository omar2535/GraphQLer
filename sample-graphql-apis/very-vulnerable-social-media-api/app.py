"""
Very Vulnerable GraphQL API — Social Media Edition
====================================================
A deliberately vulnerable GraphQL API modelling a basic social media service.
Intended for use with GraphQLer to validate UAF (use-after-delete) detection.

Intentional vulnerabilities
----------------------------
* getPost(id)   — **USE-AFTER-FREE / USE-AFTER-DELETE**: the server removes the
                  post from the owner's visible feed but keeps the data in a
                  "soft-delete" store.  getPost() still returns data for a
                  post that has been deleted, meaning any caller can access
                  content that should no longer exist.  A well-designed API
                  must return null / 404 after deletion.

Correctly secured endpoints
----------------------------
* myPosts        — only returns posts that are NOT deleted and belong to the
                   authenticated user.

Hard-coded tokens
-----------------
  Alice : Bearer alice_social_token

Usage with GraphQLer
--------------------
  graphqler --mode run \\
      --url http://localhost:8000/graphql \\
      --path ./graphqler-output \\
      --token "Bearer alice_social_token"
"""

from __future__ import annotations

import os
import uuid
from typing import Optional

import graphene
from flask import Flask, request, jsonify


# ---------------------------------------------------------------------------
# In-memory data stores
# ---------------------------------------------------------------------------

TOKENS: dict[str, str] = {
    "Bearer alice_social_token": "alice",
}

# Active posts (not soft-deleted)
posts_db: dict[str, dict] = {}

# UAF vulnerability: deleted posts are moved here instead of being truly removed
deleted_posts_db: dict[str, dict] = {}

users_db: dict[str, dict] = {
    "alice": {"id": "alice", "username": "alice", "bio": "Hello, I'm Alice!"},
}

comments_db: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Auth helpers
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

class UserType(graphene.ObjectType):
    class Meta:
        name = "User"

    id = graphene.ID(required=True)
    username = graphene.String(required=True)
    bio = graphene.String()


class PostType(graphene.ObjectType):
    class Meta:
        name = "Post"

    id = graphene.ID(required=True)
    title = graphene.String(required=True)
    body = graphene.String(required=True)
    author = graphene.String(required=True)


class CommentType(graphene.ObjectType):
    class Meta:
        name = "Comment"

    id = graphene.ID(required=True)
    post_id = graphene.ID(required=True)
    text = graphene.String(required=True)
    author = graphene.String(required=True)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

class Query(graphene.ObjectType):
    get_post = graphene.Field(
        PostType,
        id=graphene.ID(required=True),
        description="Fetch a post by ID. VULNERABLE: still returns data for deleted posts.",
    )

    my_posts = graphene.List(
        graphene.NonNull(PostType),
        description="Return posts owned by the authenticated user (soft-deleted posts excluded).",
    )

    get_user = graphene.Field(
        UserType,
        id=graphene.ID(required=True),
        description="Fetch a user profile by ID.",
    )

    get_comment = graphene.Field(
        CommentType,
        id=graphene.ID(required=True),
        description="Fetch a comment by ID.",
    )

    def resolve_get_post(self, info, id):
        require_auth()
        # VULNERABLE: check both active and soft-deleted stores
        if str(id) in posts_db:
            return PostType(**posts_db[str(id)])
        if str(id) in deleted_posts_db:
            # UAF: resource was deleted but is still served here
            return PostType(**deleted_posts_db[str(id)])
        return None

    def resolve_my_posts(self, info):
        user = require_auth()
        return [PostType(**p) for p in posts_db.values() if p["author"] == user]

    def resolve_get_user(self, info, id):
        require_auth()
        if str(id) in users_db:
            return UserType(**users_db[str(id)])
        return None

    def resolve_get_comment(self, info, id):
        require_auth()
        if str(id) in comments_db:
            return CommentType(**comments_db[str(id)])
        return None


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------

class CreatePost(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        body = graphene.String(required=True)

    post = graphene.Field(PostType)

    def mutate(self, info, title, body):
        user = require_auth()
        post_id = str(uuid.uuid4())
        post = {"id": post_id, "title": title, "body": body, "author": user}
        posts_db[post_id] = post
        return CreatePost(post=PostType(**post))


class DeletePost(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean(required=True)

    def mutate(self, info, id):
        require_auth()
        if str(id) in posts_db:
            # VULNERABLE: soft-delete only — the data is preserved in deleted_posts_db
            # so that getPost() can still return it (demonstrating UAF)
            deleted_posts_db[str(id)] = posts_db.pop(str(id))
            return DeletePost(ok=True)
        return DeletePost(ok=False)


class CreateComment(graphene.Mutation):
    class Arguments:
        post_id = graphene.ID(required=True)
        text = graphene.String(required=True)

    comment = graphene.Field(CommentType)

    def mutate(self, info, post_id, text):
        user = require_auth()
        comment_id = str(uuid.uuid4())
        comment = {"id": comment_id, "post_id": str(post_id), "text": text, "author": user}
        comments_db[comment_id] = comment
        return CreateComment(comment=CommentType(**comment))


class DeleteComment(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean(required=True)

    def mutate(self, info, id):
        require_auth()
        if str(id) in comments_db:
            del comments_db[str(id)]
            return DeleteComment(ok=True)
        return DeleteComment(ok=False)


class Mutation(graphene.ObjectType):
    create_post = CreatePost.Field()
    delete_post = DeletePost.Field()
    create_comment = CreateComment.Field()
    delete_comment = DeleteComment.Field()


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

schema = graphene.Schema(query=Query, mutation=Mutation)
app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "name": "Very Vulnerable GraphQL API — Social Media Edition",
        "description": (
            "A deliberately vulnerable social media GraphQL API for security testing. "
            "getPost() returns deleted posts (use-after-delete / UAF vulnerability)."
        ),
        "graphql_endpoint": "/graphql",
        "tokens": {
            "alice": "Bearer alice_social_token",
        },
        "uaf_vulnerable_operations": ["getPost"],
        "secure_operations": ["myPosts"],
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
    port = int(os.environ.get("PORT", 8001))
    print("=== Very Vulnerable GraphQL API — Social Media Edition ===")
    print("Tokens:")
    print("  Alice : Bearer alice_social_token")
    print("")
    print(f"GraphQL endpoint: http://localhost:{port}/graphql")
    print("")
    app.run(host="0.0.0.0", port=port, debug=False)
