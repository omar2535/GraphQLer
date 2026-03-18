"""Prompt templates for the LLM-based dependency resolver.

These are intentionally kept in a separate module so they can be tuned
independently of the resolver logic.
"""

# ── Schema context ────────────────────────────────────────────────────────────

SCHEMA_CONTEXT_HEADER = "Available GraphQL objects in this API (name: field(type), ...):\n"

# ── Mutation resolver prompt ──────────────────────────────────────────────────

MUTATION_SYSTEM_PROMPT = """\
You are an expert GraphQL API analyst. Given a GraphQL schema and a list of mutations, \
you infer semantic dependency relationships between mutations and the objects in the schema.
You always respond with valid JSON and nothing else.\
"""

MUTATION_USER_PROMPT_TEMPLATE = """\
{schema_context}

For each mutation listed below, determine:
1. "mutationType" — classify as one of:
   - "CREATE"  : the mutation creates / adds / inserts / registers a new resource
   - "UPDATE"  : the mutation modifies / edits / updates / patches an existing resource
   - "DELETE"  : the mutation removes / deletes / destroys / deactivates an existing resource
   - "UNKNOWN" : cannot be determined with confidence

2. "hardDependsOn" — a JSON object mapping input-parameter-name → ObjectName for inputs that
   are NON_NULL (required) and semantically reference an existing object in the schema.
   An input "references" an object when it would only make sense if that object already exists
   (e.g. userId references User, userEmail references User, postSlug references Post).

3. "softDependsOn" — same as hardDependsOn, but for OPTIONAL inputs.

Rules:
- Only include an input in hardDependsOn / softDependsOn if it references a KNOWN object
  from the schema context above.
- Use the EXACT object name as it appears in the schema (case-sensitive).
- If no inputs reference any objects, use empty objects {{}}.
- Do not include scalar-only references that don't relate to a schema object.

Mutations to analyse (as simplified JSON — type "T!" means NON_NULL, "[T]" means list):
{mutations_json}

Respond with a single JSON object. Each key is a mutation name; each value has exactly:
  "mutationType": string,
  "hardDependsOn": object,
  "softDependsOn": object

Example:
{{
  "createPost": {{"mutationType": "CREATE", "hardDependsOn": {{"authorId": "User"}}, "softDependsOn": {{"tagId": "Tag"}}}},
  "deleteUser": {{"mutationType": "DELETE", "hardDependsOn": {{"id": "User"}}, "softDependsOn": {{}}}}
}}\
"""

# ── Query resolver prompt ─────────────────────────────────────────────────────

QUERY_SYSTEM_PROMPT = """\
You are an expert GraphQL API analyst. Given a GraphQL schema and a list of queries, \
you infer which existing objects each query depends on in order to execute meaningfully.
You always respond with valid JSON and nothing else.\
"""

QUERY_USER_PROMPT_TEMPLATE = """\
{schema_context}

For each query listed below, determine:

1. "hardDependsOn" — a JSON object mapping input-parameter-name → ObjectName for inputs that
   are NON_NULL (required) and semantically reference an existing object in the schema.

2. "softDependsOn" — same, but for OPTIONAL inputs.

Rules:
- Only include an input in hardDependsOn / softDependsOn if it references a KNOWN object
  from the schema context above.
- Use the EXACT object name as it appears in the schema (case-sensitive).
- If no inputs reference any objects, use empty objects {{}}.

Queries to analyse (as simplified JSON — type "T!" means NON_NULL, "[T]" means list):
{queries_json}

Respond with a single JSON object. Each key is a query name; each value has exactly:
  "hardDependsOn": object,
  "softDependsOn": object

Example:
{{
  "getPost": {{"hardDependsOn": {{"id": "Post"}}, "softDependsOn": {{}}}},
  "listUserPosts": {{"hardDependsOn": {{"userId": "User"}}, "softDependsOn": {{"tagId": "Tag"}}}}
}}\
"""
