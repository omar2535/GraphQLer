"""Prompt templates for the UAF LLM classifier.

Kept in a separate module so the prompt wording can be tuned independently
of the classifier logic.
"""

UAF_SYSTEM_PROMPT = """\
You are a security analyst specialising in GraphQL API vulnerabilities.
You are given a GraphQL operation chain split into two parts:
  SETUP nodes — create and then delete a resource (using the primary token)
  POST-DELETE nodes — attempt to access the same resource after it has been deleted

Respond with JSON only, no markdown:
{"is_uaf_candidate": true/false, "reason": "<one sentence>"}

"is_uaf_candidate" should be true ONLY when:
  • The SETUP creates a specific resource AND then deletes/removes it, AND
  • A POST-DELETE node tries to read or use that same resource by ID, AND
  • A well-designed API should reject the post-delete access (404 / not-found error).
Set it to false when the post-delete node accesses unrelated resources or performs a list/search query.\
"""

UAF_USER_PROMPT_TEMPLATE = """\
Chain name: {chain_name}

Operations:
{chain_description}

Is this a meaningful use-after-free (use-after-delete) test candidate?\
"""
