# Denial of service (DoS) attack materializers
from .dos_deep_recursion_materializer import DOSDeepRecursionMaterializer
from .dos_batch_materializer import DOSBatchMaterializer
from .dos_alias_materializer import DOSAliasMaterializer
from .dos_field_duplication_materializer import DOSFieldDuplicationMaterializer
from .dos_circular_fragment_materializer import DOSCircularFragmentMaterializer
from .dos_resource_exhaustion_materializer import DOSResourceExhaustionMaterializer

# Batch the dos materializers together
dos_materializers = [
    DOSDeepRecursionMaterializer,
    DOSBatchMaterializer,
    DOSAliasMaterializer,
    DOSFieldDuplicationMaterializer,
    DOSCircularFragmentMaterializer,
    DOSResourceExhaustionMaterializer,
]
