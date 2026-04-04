"""Prompt templates for the IDOR LLM classifier.

Kept in a separate module so the prompt wording can be tuned independently
of the classifier logic.
"""

IDOR_SYSTEM_PROMPT = """\
You are a security analyst specialising in GraphQL API vulnerabilities.
You are given a GraphQL operation chain split into two parts:
  SETUP nodes — run by the resource owner (primary token)
  TEST nodes  — run by an attacker (secondary token) using IDs produced during SETUP

Respond with JSON only, no markdown:
{"is_idor_candidate": true/false, "reason": "<one sentence>"}

"is_idor_candidate" should be true ONLY when:
  • The SETUP creates a user-specific resource (order, profile, message, etc.), AND
  • The TEST node tries to read or modify that resource by ID, AND
  • A well-designed API should restrict the TEST node to the resource owner.
Set it to false for public catalogue endpoints (products, articles, public posts).\
"""

IDOR_USER_PROMPT_TEMPLATE = """\
Chain name: {chain_name}

Operations:
{chain_description}

Is this a meaningful IDOR test candidate?\
"""
