"""Shared base class for GraphQLer integration tests."""

import unittest

from graphqler import __main__
from graphqler.compiler.compiler import Compiler
from graphqler.fuzzer import Fuzzer


class GraphQLerIntegrationTestCase(unittest.TestCase):
    """Base class that provides _compile() / _fuzz() / _single() helpers.

    Subclasses must define PATH and URL class attributes.
    """

    PATH: str
    URL: str

    def _compile(self):
        """Run compile mode and return the Compiler instance."""
        compiler = Compiler(self.PATH, self.URL)
        __main__.run_compile_mode(compiler, self.PATH, self.URL)
        return compiler

    def _fuzz(self):
        """Run fuzz mode and return the Fuzzer instance."""
        fuzzer = Fuzzer(self.PATH, self.URL)
        __main__.run_fuzz_mode(fuzzer, self.PATH, self.URL)
        return fuzzer

    def _single(self, node_name: str):
        """Run single-node mode."""
        __main__.run_single_mode(self.PATH, self.URL, node_name)
