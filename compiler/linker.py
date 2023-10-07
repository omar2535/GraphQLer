"""Linker: Creates a networkx graph and stores it in a pickle file for use later on during fuzzing
The linker does the following:
- Generate a graph of object dependencies
- Attach queries to the object node
- Attach mutations related to the object node
"""
