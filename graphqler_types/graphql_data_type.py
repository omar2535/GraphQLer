class GraphqlDataType:
    def __init__(self, name: str, params: object, scalar: bool = False):
        """
        Initialization function for a GraphQL datatype

        Args:
            name (str): Name of the parameter
            params (object): An object of either a dictionary or a direct value depending on scalar
            scalar (bool, optional): If the params is a scalar. Defaults to False.
        """

        self.name = name
        self.params = params
        self.scalar = scalar
