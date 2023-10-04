"""Resolvers:
Resolverse are classes used to resolve dependencies generally or types so that we don't have to recursively look during
the traversal phase
"""
from .object_dependency_resolver import ObjectDependencyResolver
from .object_method_resolver import ObjectMethodResolver
