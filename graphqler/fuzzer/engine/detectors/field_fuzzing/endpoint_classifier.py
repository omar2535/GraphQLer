"""Endpoint privacy classifier for IDOR detection.

Two-tier classification:
  1. Heuristic  — splits endpoint/type name tokens and scores against keyword
                  lists; also inspects sensitive field names in the return type.
  2. LLM        — called only when heuristic score is ambiguous AND
                  ``config.USE_LLM`` is True.

Return values:
  "private"  — endpoint is user-scoped; IDOR enumeration should run.
  "public"   — endpoint is openly accessible; enumeration would be a false positive.
  "unknown"  — cannot determine scope; caller decides (IDEnumerationDetector skips).
"""

from __future__ import annotations

import logging
import re
from typing import Literal, cast

from graphqler import config
from graphqler.utils import llm_utils

logger = logging.getLogger(__name__)

# ── Keyword tables ────────────────────────────────────────────────────────────

# Tokens that strongly suggest the endpoint/type is user-scoped (IDOR-relevant).
_PRIVATE_TOKENS: frozenset[str] = frozenset(
    {
        # Identity / access
        "user", "users", "account", "accounts", "profile", "profiles",
        "me", "my", "own", "self", "personal", "private",
        "permission", "permissions", "role", "roles", "credential", "credentials",
        "session", "sessions", "token", "tokens",
        # Financial
        "order", "orders", "invoice", "invoices", "payment", "payments",
        "transaction", "transactions", "subscription", "subscriptions",
        "billing", "cart", "checkout", "wallet",
        # Support / workflow
        "ticket", "tickets", "case", "cases", "request", "requests",
        "task", "tasks", "assignment", "assignments",
        # Communications
        "message", "messages", "chat", "chats", "conversation", "conversations",
        "notification", "notifications", "inbox",
        # Health / regulated
        "patient", "patients", "medical", "prescription", "diagnosis",
        "employee", "employees", "staff", "hr",
        "customer", "customers", "client", "clients",
        # Generics implying "owned"
        "owned", "mine", "favourites", "favorites", "wishlist",
    }
)

# Tokens that strongly suggest the endpoint/type is publicly accessible.
_PUBLIC_TOKENS: frozenset[str] = frozenset(
    {
        # Content / catalogue
        "book", "books", "product", "products", "item", "items",
        "post", "posts", "article", "articles", "blog", "news",
        "event", "events", "category", "categories", "tag", "tags",
        "genre", "genres",
        # Media
        "movie", "movies", "film", "films", "show", "shows",
        "song", "songs", "album", "albums", "track", "tracks",
        "photo", "photos", "image", "images", "video", "videos",
        # Places / businesses
        "restaurant", "restaurants", "store", "stores",
        "location", "locations", "place", "places",
        "city", "cities", "country", "countries", "region", "regions",
        # Other catalogues
        "currency", "currencies", "language", "languages",
        "author", "authors", "publisher", "publishers",
        # Discovery
        "public", "shared", "global", "catalog", "catalogue",
        "search", "browse", "explore", "discover",
        "menu", "listing", "listings", "directory",
    }
)

# Substrings in return-type field names that indicate sensitivity / ownership.
_SENSITIVE_FIELD_PATTERNS: tuple[str, ...] = (
    "email", "password", "ssn", "social_security", "tax_id",
    "credit_card", "creditcard", "card_number", "cvv",
    "address", "phone", "mobile",
    "secret", "api_key", "apikey", "private_key",
    "balance", "salary", "income",
    "dob", "birthdate", "birth_date", "date_of_birth",
    "medical", "diagnosis", "prescription",
)

# Substrings that indicate the field links a record to a specific owner.
_OWNERSHIP_FIELD_PATTERNS: tuple[str, ...] = (
    "user_id", "userid", "owner_id", "ownerid",
    "created_by", "createdby", "customer_id", "customerid",
    "account_id", "accountid",
)

# Score thresholds (raw integer score based on token hits)
_PRIVATE_THRESHOLD = 2   # score >= this  → "private"
_PUBLIC_THRESHOLD = -1   # score <= this  → "public"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _split_name(name: str) -> list[str]:
    """Tokenise a camelCase / PascalCase / snake_case identifier into lowercase tokens."""
    # Insert a space before each uppercase letter run
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
    spaced = re.sub(r"([a-z\d])([A-Z])", r"\1 \2", spaced)
    parts = re.split(r"[\s_\-]+", spaced.lower())
    return [p for p in parts if p]


def _heuristic_score(
    endpoint_name: str,
    return_type_name: str,
    return_type_fields: list[str],
) -> int:
    """Compute a signed score indicating private (+) vs public (-) scope."""
    score = 0
    tokens = _split_name(endpoint_name) + _split_name(return_type_name or "")
    for token in tokens:
        if token in _PRIVATE_TOKENS:
            score += 2
        elif token in _PUBLIC_TOKENS:
            score -= 2

    for field in return_type_fields:
        field_lower = field.lower()
        if any(pattern in field_lower for pattern in _SENSITIVE_FIELD_PATTERNS):
            score += 1
        if any(pattern in field_lower for pattern in _OWNERSHIP_FIELD_PATTERNS):
            score += 1

    return score


# ── LLM prompt constants ──────────────────────────────────────────────────────

_ENDPOINT_SYSTEM_PROMPT = """\
You are a security analyst classifying GraphQL endpoints.
Respond with JSON only: {"scope": "private"} or {"scope": "public"}.
"private" means the endpoint returns user-specific data that should only be
accessible to the authenticated owner (IDOR is meaningful).
"public" means the endpoint returns catalogue/public data accessible to everyone.\
"""

_ENDPOINT_USER_PROMPT_TEMPLATE = """\
Endpoint name: {endpoint_name}
Return type: {return_type_name}
Return type fields: {fields_str}

Is this endpoint private (user-scoped) or public (catalogue/open)?\
"""


def _llm_classify(
    endpoint_name: str,
    return_type_name: str,
    return_type_fields: list[str],
) -> Literal["private", "public", "unknown"]:
    """Ask the configured LLM whether the endpoint is private or public.

    Uses ``graphqler.utils.llm_utils.call_llm()`` so provider configuration
    is shared with all other LLM callers.
    Returns "private", "public", or "unknown" on any error.
    """
    fields_str = ", ".join(return_type_fields[:20]) or "none"
    user_prompt = _ENDPOINT_USER_PROMPT_TEMPLATE.format(
        endpoint_name=endpoint_name,
        return_type_name=return_type_name,
        fields_str=fields_str,
    )

    try:
        data = llm_utils.call_llm(_ENDPOINT_SYSTEM_PROMPT, user_prompt)
        scope = str(data.get("scope", "")).lower()
        if scope in ("private", "public"):
            return cast(Literal["private", "public"], scope)
        logger.warning("LLM returned unexpected scope value: %r", scope)
        return "unknown"
    except ImportError:
        logger.debug("litellm not installed — skipping LLM endpoint classification")
        return "unknown"
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM endpoint classification failed: %s", exc)
        return "unknown"


# ── Public API ────────────────────────────────────────────────────────────────

class EndpointPrivacyClassifier:
    """Classify a GraphQL endpoint as private (user-scoped) or public (catalogue).

    Usage::

        clf = EndpointPrivacyClassifier()
        scope = clf.classify("getOrder", "Order", ["id", "userId", "total"])
        # → "private"

        scope = clf.classify("getBooks", "Book", ["id", "title", "author"])
        # → "public"
    """

    def classify(
        self,
        endpoint_name: str,
        return_type_name: str,
        return_type_fields: list[str],
    ) -> Literal["private", "public", "unknown"]:
        """Return the scope of the endpoint.

        Args:
            endpoint_name:      The GraphQL query/mutation name (e.g. "getUserProfile").
            return_type_name:   The name of the return type (e.g. "UserProfile").
            return_type_fields: Field names defined on the return type.

        Returns:
            "private"  — likely user-scoped; run IDOR enumeration.
            "public"   — likely open access; skip enumeration.
            "unknown"  — heuristic inconclusive (LLM also inconclusive or disabled).
        """
        score = _heuristic_score(endpoint_name, return_type_name, return_type_fields)

        if score >= _PRIVATE_THRESHOLD:
            logger.debug("Endpoint %r classified as 'private' (heuristic score %d)", endpoint_name, score)
            return "private"

        if score <= _PUBLIC_THRESHOLD:
            logger.debug("Endpoint %r classified as 'public' (heuristic score %d)", endpoint_name, score)
            return "public"

        # Ambiguous — try LLM if enabled
        if config.USE_LLM and config.LLM_USE_FOR_FUZZING:
            logger.debug("Endpoint %r is ambiguous (score %d); asking LLM", endpoint_name, score)
            return _llm_classify(endpoint_name, return_type_name, return_type_fields)

        logger.debug("Endpoint %r is ambiguous (score %d); no LLM available — returning 'unknown'", endpoint_name, score)
        return "unknown"
