from graphqler_types.graphql_data_type import GraphqlDataType
from typing import List


class GraphqlRequest:
    def __init__(
        self,
        graphqlQueryType: str,
        name: str,
        body: str,
        depends_on: List = [],
        params: List[GraphqlDataType] = [],
        res: List[GraphqlDataType] = [],
    ):
        self.name = name
        self.body = body
        self.type = graphqlQueryType
        self.depends_on = depends_on
        self.params = params
        self.res = res
