from __future__ import annotations
from .field import Field
from .query import Query
from .mutation import Mutation

from typing import List


class Object:
    def __init__(
        self,
        kind: str,
        name: str,
        fields: List[Field],
        hard_depends_on: List[Object],
        soft_depends_on: List[Object],
        associated_mutations: List[Mutation],
        associated_queries: List[Query],
    ):
        self.kind = kind
        self.name = name
        self.fields = fields
        self.hard_depends_on = hard_depends_on
        self.soft_depends_on = soft_depends_on
        self.associated_mutations = associated_mutations
        self.associated_queries = associated_queries
