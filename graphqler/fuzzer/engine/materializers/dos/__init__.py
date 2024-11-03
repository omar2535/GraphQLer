# Denial of service (DoS) attack materializers
from .dos_deep_recursion_materializer import DOSDeepRecursionMaterializer
from .dos_batch_materializer import DOSBatchMaterializer

# Batch the dos materializers together
dos_materializers = [DOSDeepRecursionMaterializer, DOSBatchMaterializer]
