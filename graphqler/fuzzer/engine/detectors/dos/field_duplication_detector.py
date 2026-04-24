"""FieldDuplicationDetector: detects servers that do not protect against field-duplication attacks.

A field-duplication attack sends a single selection set where one scalar field is repeated many
times using aliases, forcing the resolver to run N times per object returned.  A healthy server
should either deduplicate fields before execution or enforce a field-count limit.
"""

from typing import Type

from graphqler.fuzzer.engine.materializers.dos.dos_field_duplication_materializer import DOSFieldDuplicationMaterializer
from .dos_detector_base import DOSDetector


class FieldDuplicationDetector(DOSDetector):
    @property
    def DETECTION_NAME(self) -> str:
        return "DoS: Field Duplication"

    @property
    def materializer(self) -> Type[DOSFieldDuplicationMaterializer]:
        return DOSFieldDuplicationMaterializer
