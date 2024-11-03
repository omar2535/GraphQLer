from .os_command_injection.os_command_injection_detector import OSCommandInjectionDetector
from .xss_injection.xss_injection_detector import XSSInjectionDetector

from .introspection.introspection_detector import IntrospectionDetector
from .field_suggestion.field_suggestion_detector import FieldSuggestionsDetector


injection_detectors = [
    OSCommandInjectionDetector,
    XSSInjectionDetector
]

api_detectors = [
    IntrospectionDetector,
    FieldSuggestionsDetector
]
