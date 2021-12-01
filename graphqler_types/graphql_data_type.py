class GraphqlDataType:
    def __init__(self, name: str, params: object, scalar: bool = False):
        self.name = name
        self.params = params
        self.scalar = scalar
