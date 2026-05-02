from typing import Any, Generic, TypeVar

_T = TypeVar("_T")


class _SingletonCallable(Generic[_T]):
    """Callable wrapper returned by the @singleton decorator.

    Exposes the original class as ``__wrapped__`` and provides a ``reset()``
    helper that clears the cached instance (useful for test isolation).
    """

    def __init__(self, cls: type[_T]) -> None:
        self.__wrapped__: type[_T] = cls
        self._instances: dict[type[_T], _T] = {}

    def __call__(self, *args: Any, **kwargs: Any) -> _T:
        if self.__wrapped__ not in self._instances:
            self._instances[self.__wrapped__] = self.__wrapped__(*args, **kwargs)
        return self._instances[self.__wrapped__]

    def reset(self) -> None:
        """Clear the cached instance so the next call creates a fresh one."""
        self._instances.pop(self.__wrapped__, None)


def singleton(myClass: type[_T]) -> _SingletonCallable[_T]:
    return _SingletonCallable(myClass)
