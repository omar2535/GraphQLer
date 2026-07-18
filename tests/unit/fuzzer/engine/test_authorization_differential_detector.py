from unittest.mock import patch

from graphqler.fuzzer.engine.detectors.authorization_differential_detector import AuthorizationDifferentialDetector
from graphqler.fuzzer.engine.types import Result, ResultEnum
from graphqler.fuzzer.engine.types.profile import RuntimeProfile
from graphqler.utils.stats import Stats


def _result(value, payload="query { viewer { id email } }"):
    return Result(
        ResultEnum.HAS_DATA_SUCCESS,
        payload=payload,
        status_code=200,
        graphql_response={"data": {"viewer": value}},
    )


def test_anonymous_exact_match_is_confirmed():
    stats = Stats()
    primary = _result({"id": "1", "email": "a@example.test"})
    anonymous = _result({"id": "1", "email": "a@example.test"})

    with patch("graphqler.fuzzer.engine.detectors.authorization_differential_detector.detection_writer.write_from_detector"):
        AuthorizationDifferentialDetector().detect(
            "viewer",
            primary,
            [(RuntimeProfile(name="anonymous"), anonymous)],
            stats,
        )

    finding = stats.vulnerabilities["AUTHORIZATION_DIFFERENTIAL"]["viewer"]
    assert finding["is_vulnerable"] is True
    assert "anonymous" in finding["evidence"]


def test_alternate_profile_access_is_potential_not_confirmed():
    stats = Stats()
    primary = _result({"id": "1", "email": "a@example.test"})
    alternate = _result({"id": "1", "email": "a@example.test"})

    with patch("graphqler.fuzzer.engine.detectors.authorization_differential_detector.detection_writer.write_from_detector"):
        AuthorizationDifferentialDetector().detect(
            "viewer",
            primary,
            [(RuntimeProfile(name="user-b", auth_token="token-b"), alternate)],
            stats,
        )

    finding = stats.vulnerabilities["AUTHORIZATION_DIFFERENTIAL"]["viewer"]
    assert finding["is_vulnerable"] is False
    assert finding["potentially_vulnerable"] is True
    assert "user-b" in finding["evidence"]


def test_denied_profile_does_not_create_finding():
    stats = Stats()
    primary = _result({"id": "1"})
    denied = Result(ResultEnum.EXTERNAL_FAILURE, graphql_response={"errors": [{"message": "denied"}]})

    with patch("graphqler.fuzzer.engine.detectors.authorization_differential_detector.detection_writer.write_from_detector"):
        AuthorizationDifferentialDetector().detect(
            "viewer",
            primary,
            [(RuntimeProfile(name="anonymous"), denied)],
            stats,
        )

    assert "AUTHORIZATION_DIFFERENTIAL" not in stats.vulnerabilities


def test_subscription_events_are_compared():
    stats = Stats()
    primary = Result(
        ResultEnum.GENERAL_SUCCESS,
        payload="subscription { privateUpdates { id } }",
        graphql_response=[{"data": {"privateUpdates": {"id": "1"}}}],
    )
    anonymous = Result(
        ResultEnum.GENERAL_SUCCESS,
        payload=primary.payload,
        graphql_response=[{"data": {"privateUpdates": {"id": "1"}}}],
    )

    with patch("graphqler.fuzzer.engine.detectors.authorization_differential_detector.detection_writer.write_from_detector"):
        AuthorizationDifferentialDetector().detect(
            "privateUpdates",
            primary,
            [(RuntimeProfile(name="anonymous"), anonymous)],
            stats,
        )

    assert stats.vulnerabilities["AUTHORIZATION_DIFFERENTIAL"]["privateUpdates"]["is_vulnerable"] is True
