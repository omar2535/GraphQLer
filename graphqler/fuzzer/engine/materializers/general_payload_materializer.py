"""General Payload Materializer:
The single entry point for standard payload runs in fengine.

Delegates to the appropriate concrete materializer based on configuration:
  - LLMPayloadMaterializer  when config.USE_LLM is True (with fallback on failure)
  - RegularPayloadMaterializer  otherwise
"""

from __future__ import annotations

from graphqler import config
from graphqler.utils.api import API
from graphqler.utils.logging_utils import Logger
from graphqler.utils.objects_bucket import ObjectsBucket

from .llm_payload_materializer import LLMPayloadMaterializer
from .materializer import Materializer
from .regular_payload_materializer import RegularPayloadMaterializer


class GeneralPayloadMaterializer(Materializer):
    """Delegation layer that routes payload generation to the right materializer.

    fengine should always instantiate this class for standard payload runs.
    The concrete materializers (LLM, regular) are kept separate and free of
    cross-cutting concerns.
    """

    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = True):
        super().__init__(api, fail_on_hard_dependency_not_met)
        self.logger = Logger().get_fuzzer_logger().getChild(__name__)
        self._regular = RegularPayloadMaterializer(api, fail_on_hard_dependency_not_met)
        self._llm = LLMPayloadMaterializer(api, fail_on_hard_dependency_not_met)

    def get_payload(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str) -> tuple[str, dict]:
        """Return a ``(payload_string, used_objects)`` tuple.

        Uses ``LLMPayloadMaterializer`` when ``config.USE_LLM`` is enabled,
        falling back to ``RegularPayloadMaterializer`` on any error.
        Uses ``RegularPayloadMaterializer`` directly when LLM is disabled.
        """
        if not config.USE_LLM:
            return self._regular.get_payload(name, objects_bucket, graphql_type)

        try:
            return self._llm.get_payload(name, objects_bucket, graphql_type)
        except Exception as exc:
            self.logger.warning(
                "[%s] LLM materialization failed (%s); falling back to regular materializer.",
                name,
                exc,
            )
            return self._regular.get_payload(name, objects_bucket, graphql_type)
