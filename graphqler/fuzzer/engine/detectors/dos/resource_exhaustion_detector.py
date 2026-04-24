"""ResourceExhaustionDetector: detects servers that do not enforce pagination / result-set limits.

A resource exhaustion attack sends legitimate queries but with extremely large values for any
pagination-like inputs (first, limit, count, size, …).  A server that fetches and serialises
millions of rows without enforcing an upper bound is vulnerable to intentional or accidental
denial-of-service.
"""

from typing import Type

from graphqler.fuzzer.engine.materializers.dos.dos_resource_exhaustion_materializer import DOSResourceExhaustionMaterializer
from .dos_detector_base import DOSDetector


class ResourceExhaustionDetector(DOSDetector):
    @property
    def DETECTION_NAME(self) -> str:
        return "DoS: Resource Exhaustion"

    @property
    def materializer(self) -> Type[DOSResourceExhaustionMaterializer]:
        return DOSResourceExhaustionMaterializer
