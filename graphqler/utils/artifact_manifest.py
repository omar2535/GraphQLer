from __future__ import annotations

import hashlib
import importlib.metadata
from pathlib import Path
from typing import Any

from graphqler import config
from graphqler.utils.file_utils import atomic_write_json, read_json_file


class ArtifactValidationError(ValueError):
    """Compiled artifacts are missing, corrupt, or incompatible."""


_PHASE_ORDER = {"graph": 1, "chains": 2}


def _package_version() -> str:
    try:
        return importlib.metadata.version("GraphQLer")
    except importlib.metadata.PackageNotFoundError:
        return "development"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_paths(output_path: Path, settings: config.RunSettings) -> list[Path]:
    candidates = [
        output_path / settings.INTROSPECTION_RESULT_FILE_NAME,
        output_path / settings.COMPILED_OBJECTS_FILE_NAME,
        output_path / settings.COMPILED_QUERIES_FILE_NAME,
        output_path / settings.COMPILED_MUTATIONS_FILE_NAME,
        output_path / settings.COMPILED_SUBSCRIPTIONS_FILE_NAME,
    ]
    chains_dir = output_path / settings.CHAINS_DIR_NAME
    if chains_dir.exists():
        candidates.extend(path for path in chains_dir.rglob("*") if path.is_file())
    return sorted((path for path in candidates if path.exists()), key=lambda path: str(path))


def write_manifest(output_path: str | Path, endpoint: str, phase: str, settings: config.RunSettings) -> Path:
    """Write a versioned manifest and hashes for compiled artifacts."""
    if phase not in _PHASE_ORDER:
        raise ValueError(f"Unknown artifact phase: {phase}")
    root = Path(output_path)
    artifacts = {
        str(path.relative_to(root)): {
            "sha256": _sha256(path),
            "size": path.stat().st_size,
        }
        for path in _artifact_paths(root, settings)
    }
    manifest = {
        "format": "graphqler.compiled_artifacts",
        "schema_version": settings.ARTIFACT_SCHEMA_VERSION,
        "graphqler_version": _package_version(),
        "endpoint": endpoint,
        "phase": phase,
        "settings": {
            "disable_mutations": settings.DISABLE_MUTATIONS,
            "use_llm": settings.USE_LLM,
            "llm_use_for_compilation": settings.LLM_USE_FOR_COMPILATION,
        },
        "artifacts": artifacts,
    }
    manifest_path = root / settings.ARTIFACT_MANIFEST_FILE_NAME
    atomic_write_json(manifest, manifest_path)
    return manifest_path


def validate_manifest(
    output_path: str | Path,
    required_phase: str,
    settings: config.RunSettings,
    expected_endpoint: str | None = None,
) -> dict[str, Any]:
    """Validate manifest compatibility, phase, endpoint, and artifact hashes."""
    if required_phase not in _PHASE_ORDER:
        raise ValueError(f"Unknown artifact phase: {required_phase}")
    root = Path(output_path)
    manifest_path = root / settings.ARTIFACT_MANIFEST_FILE_NAME
    if not manifest_path.exists():
        raise ArtifactValidationError(f"Missing {settings.ARTIFACT_MANIFEST_FILE_NAME} in {root}; re-run compile with this GraphQLer version")
    try:
        manifest = read_json_file(manifest_path)
    except Exception as exc:
        raise ArtifactValidationError(f"Unable to read artifact manifest: {manifest_path}") from exc

    if manifest.get("format") != "graphqler.compiled_artifacts":
        raise ArtifactValidationError(f"Unsupported artifact manifest format: {manifest_path}")
    if manifest.get("schema_version") != settings.ARTIFACT_SCHEMA_VERSION:
        raise ArtifactValidationError(f"Artifact schema {manifest.get('schema_version')} is incompatible with required schema {settings.ARTIFACT_SCHEMA_VERSION}")
    actual_phase = manifest.get("phase")
    if actual_phase not in _PHASE_ORDER or _PHASE_ORDER[actual_phase] < _PHASE_ORDER[required_phase]:
        raise ArtifactValidationError(f"Artifacts are at phase {actual_phase!r}; required phase is {required_phase!r}")
    if expected_endpoint is not None and manifest.get("endpoint") != expected_endpoint:
        raise ArtifactValidationError(f"Artifacts were compiled for {manifest.get('endpoint')!r}, not {expected_endpoint!r}")

    for relative_path, metadata in manifest.get("artifacts", {}).items():
        artifact_path = root / relative_path
        if not artifact_path.is_file():
            raise ArtifactValidationError(f"Compiled artifact is missing: {artifact_path}")
        if artifact_path.stat().st_size != metadata.get("size") or _sha256(artifact_path) != metadata.get("sha256"):
            raise ArtifactValidationError(f"Compiled artifact failed integrity validation: {artifact_path}")
    return manifest
