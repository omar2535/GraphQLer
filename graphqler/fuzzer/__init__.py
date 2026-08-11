from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .fuzzer import Fuzzer

__all__ = ["Fuzzer"]


def __getattr__(name: str):
    if name == "Fuzzer":
        from .fuzzer import Fuzzer

        return Fuzzer
    raise AttributeError(name)
