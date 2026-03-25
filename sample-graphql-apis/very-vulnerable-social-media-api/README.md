# Very Vulnerable GraphQL API — Social Media Edition

A deliberately vulnerable GraphQL API that models a basic social media service.
It is designed to help validate [GraphQLer](https://github.com/omar2535/GraphQLer)'s
**use-after-free / use-after-delete (UAF)** chain detection.

## Schema overview

| Type | Fields |
|------|--------|
| `Post` | `id`, `title`, `body`, `author` |
| `Comment` | `id`, `postId`, `text`, `author` |
| `User` | `id`, `username`, `bio` |

| Operation | Type | Description |
|-----------|------|-------------|
| `createPost` | Mutation | Create a new post |
| `deletePost` | Mutation | Soft-delete a post (**vulnerable**) |
| `getPost` | Query | Fetch a post by ID (**vulnerable — serves deleted posts**) |
| `myPosts` | Query | Returns only non-deleted posts for the current user |
| `createComment` | Mutation | Add a comment to a post |
| `deleteComment` | Mutation | Delete a comment |
| `getUser` | Query | Look up a user profile |
| `getComment` | Query | Look up a comment |

## Intentional vulnerability — use-after-delete (UAF)

`deletePost(id)` performs a **soft delete**: the post record is moved from the
active store to an internal `deleted_posts_db` dictionary instead of being
truly removed. `getPost(id)` checks both stores and returns the post even when
it has been deleted.

A correct implementation would return `null` (or a 404 error) after deletion.

```
createPost(title: "hello", body: "world")  →  id = "abc"
deletePost(id: "abc")                      →  ok: true
getPost(id: "abc")                         →  Post { id: "abc", ... }  ← BUG
```

## Authentication

Hard-coded token:

| User | Token |
|------|-------|
| Alice | `Bearer alice_social_token` |

## Running locally

```bash
./start.sh
# GraphQL endpoint: http://localhost:8001/graphql
```

## Running with GraphQLer

```bash
graphqler --mode run \
    --url http://localhost:8001/graphql \
    --path ./graphqler-output \
    --token "Bearer alice_social_token"
```
