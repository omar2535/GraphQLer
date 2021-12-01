class GraphqlRequest:
    def __init__(
        self, graphqlQueryType: str, name: str, body: str, depends_on: list = [], params: list = [], res: list = []
    ):
        self.name = name
        self.body = body
        self.type = graphqlQueryType
        self.depends_on = depends_on
        self.params = params
        self.res = res
