"""Related queries to objects based on output type. We only look at the output to determine if a query is related to an object"""


class ObjectQueryResolver:
    def __init__(self):
        pass

    def resolve(self, objects: dict, queries: dict) -> dict:
        """Resolves the objects by attaching the correlated queries that output this object

        Args:
            objects (dict): The objects available
            queries (dict): The queries available

        Returns:
            dict: The objects dict enriched with a queries key
        """
        pass
