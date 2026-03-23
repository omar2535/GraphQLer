"""Simple singleton class to parse subscription listings from the introspection query"""

from .parser import Parser


class SubscriptionListParser(Parser):
    def __init__(self):
        pass

    def __extract_arg_info(self, field):
        input_args = {}
        for arg in field:
            arg_info = {
                "name": arg["name"],
                "type": arg["type"]["name"] if "name" in arg["type"] else None,
                "kind": arg["type"]["kind"] if "kind" in arg["type"] else None,
                "ofType": self.extract_oftype(arg["type"]),
            }
            input_args[arg["name"]] = arg_info
        return input_args

    def parse(self, introspection_data: dict) -> dict:
        """Parses the introspection data for subscription operations

        Args:
            introspection_data (dict): Introspection JSON as a dictionary

        Returns:
            dict: Dict of subscriptions with their input/output types
        """
        schema_types = introspection_data.get("data", {}).get("__schema", {}).get("types", [])
        subscription_type_info = introspection_data.get("data", {}).get("__schema", {}).get("subscriptionType", None)

        if subscription_type_info is None:
            return {}

        subscription_type_name = subscription_type_info.get("name", "Subscription")
        subscription_objects = [t for t in schema_types if t.get("kind") == "OBJECT" and t.get("name") == subscription_type_name]

        if len(subscription_objects) == 0:
            return {}

        subscriptions = subscription_objects[0]["fields"]

        subscription_info_dict = {}
        for subscription in subscriptions:
            subscription_name = subscription["name"]
            subscription_args = self.__extract_arg_info(subscription["args"])
            return_type = {
                "kind": subscription["type"].get("kind"),
                "name": subscription["type"].get("name"),
                "ofType": self.extract_oftype(subscription["type"]),
                "type": subscription["type"].get("name"),
            }

            subscription_info_dict[subscription_name] = {
                "name": subscription_name,
                "inputs": subscription_args,
                "output": return_type,
            }

        return subscription_info_dict
