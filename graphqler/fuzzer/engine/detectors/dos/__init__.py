from .field_duplication_detector import FieldDuplicationDetector
from .circular_fragment_detector import CircularFragmentDetector
from .resource_exhaustion_detector import ResourceExhaustionDetector

dos_detectors = [
    FieldDuplicationDetector,
    CircularFragmentDetector,
    ResourceExhaustionDetector,
]

__all__ = [
    "FieldDuplicationDetector",
    "CircularFragmentDetector",
    "ResourceExhaustionDetector",
    "dos_detectors",
]
