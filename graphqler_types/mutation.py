from typing import List
from graphqler_types import Input, Output, Object


class Mutation:
    def __init__(
        self,
        name: str,
        mutation_type: str,
        inputs: List[Input],
        output: Output,
        hard_depends_on: dict,
        soft_depends_on: dict,
        is_deprecated: bool = False,
    ):
        self.name = name
        self.mutation_type = mutation_type
        self.inputs = inputs
        self.output = output
        self.hard_depends_on = hard_depends_on
        self.soft_depends_on = soft_depends_on
        self.is_deprecated = is_deprecated
        pass
