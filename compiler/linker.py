"""Linker: Creates a networkx graph and stores it in a pickle file for use later on during fuzzing
The linker does the following:
- Serialize all the objects (Objects, Queries, Mutations, InputObjects, Enums)
- Generate a graph of object dependencies
- Attach queries to the object node
- Attach mutations related to the object node
"""
