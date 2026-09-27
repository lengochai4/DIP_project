"""Run identity and reproducibility metadata helpers."""

from __future__ import annotations

import platform
import subprocess
import uuid
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

from dip_touchless.configuration import ResolvedConfig


def create_run_id() -> str:
    """Create a human-readable unique run identifier."""

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )

    suffix = uuid.uuid4().hex[:8]

    return f"{timestamp}-{suffix}"


def _git_revision() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ):
        return None

    revision = result.stdout.strip()

    return revision or None


def _dependency_version(
    distribution_name: str,
) -> str | None:
    try:
        return importlib_metadata.version(distribution_name)
    except importlib_metadata.PackageNotFoundError:
        return None


def build_run_metadata(
    resolved: ResolvedConfig,
    *,
    run_id: str | None = None,
    spec_version: str = "canonical-v1.2",
    code_revision: str | None = None,
) -> dict[str, Any]:
    """Build run metadata without inventing unavailable observations."""

    config = resolved.to_dict()

    experiment = config["experiment"]
    camera = config["camera"]
    runtime = config["runtime"]
    tracking = config["tracking"]
    logging_config = config["logging"]

    model_path = tracking.get("model_path")

    model_filename = (
        Path(model_path).name
        if model_path
        else None
    )

    return {
        "run_id": run_id or create_run_id(),
        "experiment_id": experiment.get("experiment_id"),
        "condition": experiment.get("condition"),
        "trial_id": experiment.get("trial_id"),
        "spec_version": spec_version,
        "code_revision": code_revision or _git_revision(),
        "log_schema_version": logging_config["schema_version"],
        "config_hash": resolved.sha256,
        "python_version": platform.python_version(),
        "dependency_versions": {
            "PyYAML": _dependency_version("PyYAML"),
        },
        "provider": {
            "name": tracking.get("provider"),
            "model_filename": model_filename,
            "model_checksum": None,
        },
        "camera": {
            "backend": camera.get("backend"),
            "requested": {
                "width": camera.get("width"),
                "height": camera.get("height"),
                "fps": camera.get("requested_fps"),
            },
            "observed": None,
        },
        "source_data": {
            "identity": runtime.get("replay_source"),
            "sha256": None,
        },
        "system": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor() or None,
        },
    }