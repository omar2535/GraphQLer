from typing import Protocol, Callable, Union, Tuple, runtime_checkable
from requests import Session, Response

@runtime_checkable
class RequestUtilsProtocol(Protocol):
    # Global variables
    last_request_time: float
    session: Union[Session, None]

    # Functions
    def get_headers(self) -> dict:
        """Get the headers for the request"""
        ...

    def get_proxies(self) -> dict:
        """Get the proxies for the request"""
        ...

    def send_graphql_request(
        self,
        url: str,
        payload: Union[str, dict, list],
        next: Callable[[dict], dict] | None = None
    ) -> Tuple[dict, Response]:
        """Send GraphQL request to the specified endpoint"""
        ...

    def parse_response(self, response_text: str) -> dict:
        """Parse the response and try to jsonify it"""
        ...

    def get_or_create_session(self) -> Session:
        """Gets an existing session or creates a new one"""
        ...

    def create_new_session(self) -> Session:
        """Create a new session"""
        ...
