from .os_command_injection.os_command_injection_detector import OSCommandInjectionDetector
from .xss_injection.xss_injection_detector import XSSInjectionDetector
from .ssrf_injection.ssrf_injection_detector import SSRFInjectionDetector
from .sql_injection.sql_injection_detector import SQLInjectionDetector

from .introspection.introspection_detector import IntrospectionDetector
from .field_suggestion.field_suggestion_detector import FieldSuggestionsDetector


injection_detectors = [
    OSCommandInjectionDetector,
    XSSInjectionDetector,
    SSRFInjectionDetector,
    SQLInjectionDetector
]

api_detectors = [
    IntrospectionDetector,
    FieldSuggestionsDetector
]
