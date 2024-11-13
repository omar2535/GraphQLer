from abc import ABC, abstractmethod
from typing import Type

import requests

from graphqler.graph.node import Node
from graphqler.utils.api import API
from graphqler.utils.logging_utils import Logger
from graphqler.utils.objects_bucket import ObjectsBucket
from graphqler.utils.stats import Stats
from graphqler.utils import plugins_handler
from graphqler.fuzzer.engine.types import ResultEnum, Result

from ..materializers.materializer import Materializer


class Detector(ABC):
    """Base Detector class that implements common functionality for all detectors.

    Subclasses must implement:
    - DETECTION_NAME (class attribute)
    - materializer (property)
    - _is_vulnerable (method)
    """

    @property
    @abstractmethod
    def DETECTION_NAME(self) -> str:
        """Name of the detection type"""
        pass

    @property
    def detect_only_once_for_api(self) -> bool:
        """Whether the detector should be run only once on the API"""
        return False

    @property
    def detect_only_once_for_node(self) -> bool:
        """Whether the detector should be run only once on the node"""
        return True

    @property
    @abstractmethod
    def materializer(self) -> Type[Materializer]:
        """Materializer class to be used for payload generation"""
        pass

    def __init__(self, api: API, node: Node, objects_bucket: ObjectsBucket, graphql_type: str):
        self.api = api
        self.node = node
        self.name = node.name
        self.objects_bucket = objects_bucket
        self.graphql_type = graphql_type
        self.detector_logger = Logger().get_detector_logger()
        self.fuzzer_logger = Logger().get_fuzzer_logger()
        self.payload = ""
        self.confirmed_vulnerable = False
        self.potentially_vulnerable = False

    def detect(self) -> tuple[bool, bool]:
        """Main function to run to detect the vulnerability.

        Returns:
            tuple[bool, bool]: (confirmed_vulnerable, potentially_vulnerable)
        """
        self.payload = self.get_payload()
        self.fuzzer_logger.debug(f"[Fuzzer] Payload:\n{self.payload}")
        self.detector_logger.info(f"[Detector] Payload:\n{self.payload}")

        # Send the GraphQL request
        graphql_response, request_response = plugins_handler.get_request_utils().send_graphql_request(self.api.url, self.payload)
        result = Result(
            result_enum=ResultEnum.GENERAL_SUCCESS,
            payload=self.payload,
            status_code=request_response.status_code,
            graphql_response=graphql_response,
            raw_response_text=request_response.text
        )
        Stats().add_http_status_code(self.name, request_response.status_code)
        Stats().update_stats_from_result(self.node, result)

        self.detector_logger.info(f"[{request_response.status_code}]Response: {request_response.text}")
        self.fuzzer_logger.info(f"[{request_response.status_code}]Response: {graphql_response}")

        self._parse_response(graphql_response, request_response)
        Stats().add_vulnerability(self.DETECTION_NAME, self.name, self.confirmed_vulnerable, self.potentially_vulnerable)
        return (self.confirmed_vulnerable, self.potentially_vulnerable)

    def get_payload(self) -> str:
        """Gets the materialized payload to be sent to the API"""
        materializer_instance = self.materializer(
            api=self.api,
            fail_on_hard_dependency_not_met=False,
            max_depth=3
        )
        payload, used_objects = materializer_instance.get_payload(self.name, self.objects_bucket, self.graphql_type)
        return payload

    def _parse_response(self, graphql_response: dict, request_response: requests.Response):
        """Parses the response and checks for vulnerability"""
        if "errors" in graphql_response:
            self.detector_logger.info(f"Got errors: {graphql_response['errors']}")
            # self.potentially_vulnerable = True
        if self._is_vulnerable(graphql_response, request_response):
            self.detector_logger.info(f"Vulnerable to {self.DETECTION_NAME}")
            self.confirmed_vulnerable = True
        if self._is_potentially_vulnerable(graphql_response, request_response):
            self.detector_logger.info(f"Potentially vulnerable to {self.DETECTION_NAME}")
            self.potentially_vulnerable = True

    @abstractmethod
    def _is_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        """Checks if the response indicates a vulnerability.

        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def _is_potentially_vulnerable(self, graphql_response: dict, request_response: requests.Response) -> bool:
        """Checks if the response indicates a potential vulnerability.

        Must be implemented by subclasses.
        """
        pass
