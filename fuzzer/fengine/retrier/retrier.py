""" Retrier
This moule will retry any immediate errors that arise during the query. This is not responsible for running the same query / mutation again,
rather, it's responsible for modifying the query / mutation to make it work. Scenarios:
- We have a NON-NULL column that is selected for in the output, but the server is responding with NULL, you will get the following error:
  {'message': 'Cannot return null for non-nullable field Transaction.payer.'}.
  In this scenario, we will need to remove the payer key from the mutation / query output fields
"""

from .utils import find_block_end, remove_lines_within_range


class Retrier:
    def __init__(self):
        pass
