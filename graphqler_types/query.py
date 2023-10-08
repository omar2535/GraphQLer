"""Internal query type - has the basic query type information + enrichment information from the resolving stage"""

from typing import List
from graphqler_types import Input
from graphqler_types import Output


class Query:
    def __init__(self, name: str, inputs: List[Input], output: Output, soft_depends_on: dict, hard_depends_on: dict):
        self.name = name
        self.inputs = inputs
        self.output = output
        self.soft_depends_on = soft_depends_on
        self.hard_depends_on = hard_depends_on
