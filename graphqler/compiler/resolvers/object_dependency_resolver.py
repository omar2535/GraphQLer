"""This module will be used to create a object dependency resolver
The representation of this will be essentially a text-based graph

The dependencies will be generated from object - object
while methods such as queries / mutations will be related to objects
based on either output type or semantic understanding
"""

from graphqler.config import BUILT_IN_TYPES, BUILT_IN_TYPE_KINDS


class ObjectDependencyResolver:
    def __init__(self):
        pass

    def resolve(self, objects) -> dict:
        """Resolve dependencies by adding the 'hardDependsOn' key and 'softDependsOn' key
           hardDependsOn: the object must be created for this object to be instantiated
           softDependsOn: the object can be null on instantiation of this object

        Returns:
            dict: The new enriched objects with an extra 'dependsOn' key
        """
        for gql_object_key, gql_object in objects.items():
            objects[gql_object_key] = self.parse_gql_object(gql_object)

        return objects

    def get_base_oftype(self, oftype: dict) -> dict:
        if "ofType" in oftype and oftype["ofType"] is not None:
            return self.get_base_oftype(oftype["ofType"])
        else:
            return oftype

    def parse_gql_object(self, gql_object: dict) -> dict:
        """Parse a single object, noting down all of the other object this object depends on
           hardDependsOn: Where the object has fields on other objects and it's kind is NON_NULL
           softDependsOn: Where the object has fields on other objects and it can be NULL


           !weird edge cases found from this method:
           - when the field kind is a SCALAR, the ofType will be null

        Args:
            gql_object (dict): The graphql object

        Returns:
            dict: The enriched object with extra 'softDependsOn' key and 'hardDependsOn'
        """
        soft_dependent_objects = []
        hard_dependent_objects = []
        for field in gql_object["fields"]:
            # There are 3 cases:
            # - if the kind is SCALAR/OBJECT/INTERFACE/UNION/ENUM/INPUT_OBJECT,
            # - if kind is NON_NULL
            # - if kind is LIST
            if field["kind"] in BUILT_IN_TYPE_KINDS and field["kind"] != "NON_NULL" and field["kind"] != "LIST":
                if field["type"] not in BUILT_IN_TYPES:
                    soft_dependent_objects.append(field["type"])
            if field["kind"] == "NON_NULL":
                base_oftype = self.get_base_oftype(field["ofType"])
                if base_oftype["kind"] not in BUILT_IN_TYPES:
                    hard_dependent_objects.append(base_oftype["name"])
            elif field["kind"] == "LIST":
                base_oftype = self.get_base_oftype(field["ofType"])
                if base_oftype["kind"] not in BUILT_IN_TYPES:
                    # TODO: Figure out if lists can have hard dependencies (a non-zero lengthed list)
                    soft_dependent_objects.append(base_oftype["name"])

        # TODO: Figure out a way see if we can handle custom scalars dynamically (?) - right now, they show up as none
        # Remove nulls from dependency list and make them unique
        soft_dependent_objects = list(set([o for o in soft_dependent_objects if o is not None]))
        hard_dependent_objects = list(set([o for o in hard_dependent_objects if o is not None]))

        gql_object["softDependsOn"] = soft_dependent_objects
        gql_object["hardDependsOn"] = hard_dependent_objects
        return gql_object
