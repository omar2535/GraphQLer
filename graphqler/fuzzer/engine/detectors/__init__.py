from .os_command_injection.os_command_injection_detector import OSCommandInjectionDetector
from .xss_injection.xss_injection_detector import XSSInjectionDetector
from .ssrf_injection.ssrf_injection_detector import SSRFInjectionDetector
from .sql_injection.sql_injection_detector import SQLInjectionDetector
from .nosql_injection.nosql_injection_detector import NoSQLInjectionDetector
from .time_sql_injection.time_sql_injection_detector import TimeSQLInjectionDetector
from .query_deny_bypass.query_deny_bypass_detector import QueryDenyBypassDetector
from .path_injection.path_injection_detector import PathInjectionDetector
from .field_fuzzing.field_charset_fuzzing_detector import FieldCharsetFuzzingDetector
from .field_fuzzing.id_enumeration_detector import IDEnumerationDetector
from .idor_chain_detector import IDORChainDetector as IDORChainDetector
from .uaf_chain_detector import UAFChainDetector as UAFChainDetector
from .cursor_chain_detector import CursorChainDetector as CursorChainDetector

from .introspection.introspection_detector import IntrospectionDetector
from .field_suggestion.field_suggestion_detector import FieldSuggestionsDetector


injection_detectors = [
    OSCommandInjectionDetector,
    XSSInjectionDetector,
    SSRFInjectionDetector,
    SQLInjectionDetector,
    NoSQLInjectionDetector,
    TimeSQLInjectionDetector,
    PathInjectionDetector
]

misc_detectors = [
    QueryDenyBypassDetector
]

enumeration_detectors = [
    FieldCharsetFuzzingDetector,
    IDEnumerationDetector,
]

api_detectors = [
    IntrospectionDetector,
    FieldSuggestionsDetector
]
