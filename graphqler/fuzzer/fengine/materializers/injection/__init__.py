from .sql_injection_materializer import SQLInjectionMaterializer
from .html_injection_materializer import HTMLInjectionMaterializer
from .xss_injection_materializer import XSSInjectionMaterializer
from .path_traversal_injection_materializer import PathTraversalInjectionMaterializer

injection_materializers = [
    SQLInjectionMaterializer,
    HTMLInjectionMaterializer,
    XSSInjectionMaterializer,
    PathTraversalInjectionMaterializer
]
