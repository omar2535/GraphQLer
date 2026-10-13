import json

import pytest

from graphqler import config
from graphqler.utils.artifact_manifest import ArtifactValidationError, validate_manifest, write_manifest


def _compiled_files(root, settings):
    files = [
        settings.INTROSPECTION_RESULT_FILE_NAME,
        settings.COMPILED_OBJECTS_FILE_NAME,
        settings.COMPILED_QUERIES_FILE_NAME,
        settings.COMPILED_MUTATIONS_FILE_NAME,
        settings.COMPILED_SUBSCRIPTIONS_FILE_NAME,
    ]
    for index, relative_path in enumerate(files):
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"artifact-{index}")


def test_manifest_round_trip_validates_hashes_and_endpoint(tmp_path):
    settings = config.snapshot()
    _compiled_files(tmp_path, settings)
    write_manifest(tmp_path, "https://example.test/graphql", "chains", settings)

    manifest = validate_manifest(
        tmp_path,
        "chains",
        settings,
        expected_endpoint="https://example.test/graphql",
    )

    assert manifest["schema_version"] == settings.ARTIFACT_SCHEMA_VERSION
    assert manifest["phase"] == "chains"
    assert len(manifest["artifacts"]) == 5


def test_manifest_rejects_tampered_artifact(tmp_path):
    settings = config.snapshot()
    _compiled_files(tmp_path, settings)
    write_manifest(tmp_path, "https://example.test/graphql", "chains", settings)
    (tmp_path / settings.COMPILED_QUERIES_FILE_NAME).write_text("tampered")

    with pytest.raises(ArtifactValidationError, match="integrity validation"):
        validate_manifest(tmp_path, "chains", settings)


def test_manifest_rejects_wrong_endpoint_and_incomplete_phase(tmp_path):
    settings = config.snapshot()
    _compiled_files(tmp_path, settings)
    write_manifest(tmp_path, "https://first.test/graphql", "graph", settings)

    with pytest.raises(ArtifactValidationError, match="required phase"):
        validate_manifest(tmp_path, "chains", settings)
    with pytest.raises(ArtifactValidationError, match="not 'https://second.test/graphql'"):
        validate_manifest(tmp_path, "graph", settings, expected_endpoint="https://second.test/graphql")


def test_manifest_rejects_incompatible_schema(tmp_path):
    settings = config.snapshot()
    manifest_path = tmp_path / settings.ARTIFACT_MANIFEST_FILE_NAME
    manifest_path.write_text(
        json.dumps(
            {
                "format": "graphqler.compiled_artifacts",
                "schema_version": 999,
                "phase": "chains",
                "artifacts": {},
            }
        )
    )

    with pytest.raises(ArtifactValidationError, match="incompatible"):
        validate_manifest(tmp_path, "chains", settings)
