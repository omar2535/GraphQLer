from .os_command_injection.os_command_injection_detector import OSCommandInjectionDetector
from .xss_injection.xss_injection_detector import XSSInjectionDetector

from .introspection.introspection_detector import IntrospectionDetector


injection_detectors = [
    OSCommandInjectionDetector,
    XSSInjectionDetector
]

api_detectors = [
    IntrospectionDetector
]
