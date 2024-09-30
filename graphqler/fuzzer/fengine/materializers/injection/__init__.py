from .sql_injection_materializer import SQLInjectionMaterializer
from .html_injection_materializer import HTMLInjectionMaterializer

injection_materializers = [
    SQLInjectionMaterializer,
    HTMLInjectionMaterializer
]
