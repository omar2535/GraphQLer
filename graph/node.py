"""A node object
Graphql type: One of [Object, Query, Mutation]
"""


class Node:
    def __init__(self, graphql_type: str, name: str, body: dict):
        """Initialize a node, saving information about the graphql type

        Args:
            graphql_type (str): One of [Object, Query, Mutation]
            name (str): The name of the grpahql object
            body (dict): The body of the graphql type
        """
        self.graphql_type = graphql_type
        self.name = name
        self.body = body

    def __str__(self):
        return f"Node({self.graphql_type} | {self.name})"

    def __repr__(self):
        return f"Node({self.graphql_type} | {self.name})"
