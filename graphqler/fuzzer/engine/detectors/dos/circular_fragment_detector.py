"""CircularFragmentDetector: detects servers that do not protect against circular fragment attacks.

The GraphQL specification (June 2018, §5.5.2.2) forbids fragment cycles.  A compliant server must
detect the cycle during validation and immediately return a descriptive error — without executing
the query.  Servers that skip this validation check may loop indefinitely or exhaust stack memory.
"""

from typing import Type

from graphqler.fuzzer.engine.materializers.dos.dos_circular_fragment_materializer import DOSCircularFragmentMaterializer
from .dos_detector_base import DOSDetector


class CircularFragmentDetector(DOSDetector):
    @property
    def DETECTION_NAME(self) -> str:
        return "DoS: Circular Fragment"

    @property
    def materializer(self) -> Type[DOSCircularFragmentMaterializer]:
        return DOSCircularFragmentMaterializer
