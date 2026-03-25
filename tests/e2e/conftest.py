import pytest


@pytest.fixture(autouse=True, scope="function")
def reset_singletons():
    """Reset singleton instances before and after each test method.

    When pytest-xdist uses fewer workers than test files, multiple test
    modules run sequentially in the same worker process. Singletons
    (Stats, ObjectsBucket, FEngine) would otherwise retain stale file
    paths and state from a previous test, causing FileNotFoundErrors and
    empty-bucket assertion failures.

    Function scope is required because module-scoped fixtures are not
    reliably triggered between unittest.TestCase test files.
    """
    from graphqler.utils.stats import Stats
    from graphqler.utils.objects_bucket import ObjectsBucket
    from graphqler.fuzzer.engine.fengine import FEngine

    Stats.reset()  # ty: ignore[unresolved-attribute]
    ObjectsBucket.reset()  # ty: ignore[unresolved-attribute]
    FEngine.reset()  # ty: ignore[unresolved-attribute]
    yield
    Stats.reset()  # ty: ignore[unresolved-attribute]
    ObjectsBucket.reset()  # ty: ignore[unresolved-attribute]
    FEngine.reset()  # ty: ignore[unresolved-attribute]
