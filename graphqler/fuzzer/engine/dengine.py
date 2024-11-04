from .detectors import injection_detectors
from .detectors import api_detectors
from .detectors import misc_detectors
from .detectors.detector import Detector
from graphqler.utils.api import API
from graphqler.utils.logging_utils import Logger
from graphqler.utils.objects_bucket import ObjectsBucket

import graphqler.config as config


class DEngine:
    """Detector engine module
    -- used to detect vulnerabilities in the API
    """

    def __init__(self, api: API):
        """The intiialization of the DEngine

        Args:
            api (API): The API object
        """
        self.api = api
        self.logger = Logger().get_detector_logger()
        self.nodes_ran: dict[str, dict[str, bool]] = {}  # {node_name: {detection_name: True/False}}

    def run_detections_on_api(self):
        """Run detections on the API
           - Uses API as the key for nodes_ran marking
        """
        for api_detector in api_detectors:
            detector = api_detector(api=self.api, name=self.api.url, objects_bucket=ObjectsBucket(self.api), graphql_type="")
            if not self.__should_run_detection(detector, self.api.url):
                continue
            is_vulnerable, potentially_vulnerable = detector.detect()
            self.logger.info(f"Detector {detector.DETECTION_NAME} finished detecting - is_vulnerable: {is_vulnerable} - potentially_vulnerable: {potentially_vulnerable}")
            self.__add_ran_node(self.api.url, detector.DETECTION_NAME)

    def run_detections_on_graphql_object(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str):
        """Runs all detectors on a specific GraphQL object (either QUERY or MUTATION)

        Args:
            name (str): Name of the query or mutation
            objects_bucket (ObjectsBucket): The objects bucket
            graphql_type (str): The GraphQL type
        """
        if not config.SKIP_INJECTION_ATTACKS:
            self.__run_injection_detections(name, objects_bucket, graphql_type)

        if not config.SKIP_MISC_ATTACKS:
            self.__run_misc_detections(name, objects_bucket, graphql_type)

    def __run_misc_detections(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str):
        """Runs miscellaneous detections

        Args:
            name (str): The name of the node
            objects_bucket (ObjectsBucket): The objects bucket
            graphql_type (str): The type of the GraphQL operation
        """
        for misc_detector in misc_detectors:
            detector = misc_detector(api=self.api, name=name, objects_bucket=objects_bucket, graphql_type=graphql_type)
            if not self.__should_run_detection(detector, name):
                continue
            is_vulnerable, potentially_vulnerable = detector.detect()
            self.logger.info(f"Detector {detector.DETECTION_NAME} finished detecting - is_vulnerable: {is_vulnerable} - potentially_vulnerable: {potentially_vulnerable}")
            self.__add_ran_node(name, detector.DETECTION_NAME)

    def __run_injection_detections(self, name: str, objects_bucket: ObjectsBucket, graphql_type: str):
        """Runs injection detections

        Args:
            name (str): The name of the node
            objects_bucket (ObjectsBucket): The objects bucket
            graphql_type (str): The type of the GraphQL operation
        """
        for injection_detector in injection_detectors:
            detector = injection_detector(api=self.api, name=name, objects_bucket=objects_bucket, graphql_type=graphql_type)
            if not self.__should_run_detection(detector, name):
                continue
            is_vulnerable, potentially_vulnerable = detector.detect()
            self.logger.info(f"Detector {detector.DETECTION_NAME} finished detecting - is_vulnerable: {is_vulnerable} - potentially_vulnerable: {potentially_vulnerable}")
            self.__add_ran_node(name, detector.DETECTION_NAME)

    def __add_ran_node(self, name: str, detection_name: str):
        """Adds the node to the ran nodes list

        Args:
            name (str): The name of the node
            detection_name (str): The name of the detection
        """
        if name not in self.nodes_ran:
            self.nodes_ran[name] = {}
        self.nodes_ran[name][detection_name] = True

    def __should_run_detection(self, detector: Detector, name: str) -> bool:
        """Whether the detection should be ran

        Args:
            detector (Detector): The detector object
            name (str): The name of the node

        Returns:
            bool: Whether the detection should be ran
        """
        # First, check if the detector should be ran only once on the node
        if detector.detect_only_once_for_node:
            if name in self.nodes_ran and detector.DETECTION_NAME in self.nodes_ran[name]:
                return False

        # Next, check if the detector should be run only once on the API
        if detector.detect_only_once_for_api:
            for node in self.nodes_ran:
                if detector.DETECTION_NAME in self.nodes_ran[node]:
                    return False
        return True
