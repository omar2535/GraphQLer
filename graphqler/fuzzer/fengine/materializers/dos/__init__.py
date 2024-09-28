# Denial of service (DoS) attack materializers
from .dos_deep_recursion_materializer import DOSDeepRecursionMaterializer

# Batch the dos materializers together
dos_materializers = [
    DOSDeepRecursionMaterializer
]
