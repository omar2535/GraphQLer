from typing import Type, override

import requests

from graphqler.utils.api import API
from graphqler.fuzzer.engine.materializers.getter import Getter
from graphqler.fuzzer.engine.detectors.detector import Detector
from graphqler.fuzzer.engine.materializers.utils.materialization_utils import prettify_graphql_payload
from graphqler.fuzzer.engine.materializers.regular_payload_materializer import RegularPayloadMaterializer
from graphqler.utils.request_utils import send_graphql_request
from graphqler.utils.objects_bucket import ObjectsBucket
from graphqler.utils.stats import Stats


class QueryDenyBypassMaterializer(RegularPayloadMaterializer):
    def __init__(self, api: API, fail_on_hard_dependency_not_met: bool = False, max_depth: int = 20):
        super().__init__(api, fail_on_hard_dependency_not_met)
        self.api = api
        self.fail_on_hard_dependency_not_met = fail_on_hard_dependency_not_met
        self.getter = Getter()

    def get_non_aliased_payload(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str) -> tuple[str, dict]:
        if graphql_type == "Query":
            return self._get_query_payload(name, objects_bucket)
        if graphql_type == "Mutation":
            return self._get_mutation_payload(name, objects_bucket)
        else:
            return "", {}

    def get_aliased_payload(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str) -> tuple[str, dict]:
        if graphql_type not in ["Query", "Mutation"]:
            return "", {}
        info = self.api.queries[name] if graphql_type == "Query" else self.api.mutations[name]
        inputs = self.materialize_inputs(info, info["inputs"], objects_bucket, max_depth=3)
        output = self.materialize_output(info, info["output"], objects_bucket, max_depth=3)

        if graphql_type == "Query":
            if inputs != "":
                inputs = f"({inputs})"

            payload = f"""
            query {{
                s: {name} {inputs}
                {output}
            }}
            """
        else:
            if inputs.strip() == "":
                payload = f"""
                mutation {{
                    {name}
                    {output}
                }}
                """
            else:
                payload = f"""
                mutation {{
                    {name} (
                        {inputs}
                    )
                    {output}
                }}
                """
        pretty_payload = prettify_graphql_payload(payload)
        return pretty_payload, {}


class QueryDenyBypassDetector(Detector):
    @property
    def DETECTION_NAME(self) -> str:
        return "Query deny bypass"

    @property
    def detect_only_once_for_api(self) -> bool:
        return False

    @property
    def detect_only_once_for_node(self) -> bool:
        return True

    @property
    def materializer(self) -> Type[QueryDenyBypassMaterializer]:
        return QueryDenyBypassMaterializer

    @override
    def detect(self) -> tuple[bool, bool]:
        """Detects deny bypass vulnerability
           Does this in two phases - first, send the first request, if it's blocked, sends the second request with alias
           A deny bypass vulnerability is detected if the second request is successful

        Returns:
            tuple[bool, bool]: is_vulnerable, is_potentially_vulnerable
        """
        # If it's not a query, just skip
        if self.graphql_type != "Query":
            return (False, False)

        materializer_instance = self.materializer(api=self.api, fail_on_hard_dependency_not_met=False, max_depth=3)
        non_aliased_payload, _ = materializer_instance.get_non_aliased_payload(self.name, self.objects_bucket, self.graphql_type)
        self.fuzzer_logger.debug(f"Non-aliased Payload:\n{non_aliased_payload}")
        self.detector_logger.info(f"Non-aliased Payload:\n{non_aliased_payload}")
        non_aliased_graphql_response, non_aliased_request_response = send_graphql_request(self.api.url, non_aliased_payload)

        aliased_payload, _ = materializer_instance.get_aliased_payload(self.name, self.objects_bucket, self.graphql_type)
        self.fuzzer_logger.debug(f"Aliased Payload:\n{aliased_payload}")
        self.detector_logger.info(f"Aliased Payload:\n{aliased_payload}")
        aliased_graphql_response, aliased_request_response = send_graphql_request(self.api.url, aliased_payload)

        if (("400" in non_aliased_request_response.text and 'errors' in non_aliased_graphql_response)
                or non_aliased_request_response.status_code == 400):
            if aliased_request_response.status_code == 200 and aliased_graphql_response['data']:
                self.confirmed_vulnerable = True
                self.potentially_vulnerable = True
        else:
            self.potentially_vulnerable = False
            self.confirmed_vulnerable = False
        Stats().add_http_status_code(self.name, non_aliased_request_response.status_code)
        Stats().add_http_status_code(self.name, aliased_request_response.status_code)
        Stats().add_vulnerability(self.DETECTION_NAME, self.name, self.confirmed_vulnerable, self.potentially_vulnerable)
        return (self.confirmed_vulnerable, self.potentially_vulnerable)

    def _is_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        raise NotImplementedError()

    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        raise NotImplementedError()
