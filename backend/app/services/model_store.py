from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import joblib

DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "sentinel_baseline"


class ModelIntegrityError(RuntimeError):
    """Raised before deserialization when a frozen model checksum does not match."""


def ensure_model_dir(path: str | Path | None = None) -> Path:
    target = Path(path) if path else DEFAULT_MODEL_DIR
    target.mkdir(parents=True, exist_ok=True)
    return target


def save_bundle(bundle: dict[str, Any], manifest: dict[str, Any], path: str | Path | None = None) -> dict[str, str]:
    target = ensure_model_dir(path)
    bundle_path = target / "sentinel_baseline.joblib"
    manifest_path = target / "model_manifest.json"
    joblib.dump(bundle, bundle_path)
    digest = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    manifest = {**manifest, "artifact_sha256": digest}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"bundle": str(bundle_path), "manifest": str(manifest_path), "sha256": digest}


def load_bundle(path: str | Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    target = Path(path) if path else DEFAULT_MODEL_DIR
    bundle_path = target / "sentinel_baseline.joblib"
    manifest_path = target / "model_manifest.json"
    if not bundle_path.exists() or not manifest_path.exists():
        raise FileNotFoundError(f"No trained Sentinel model found at {target}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = str(manifest.get("artifact_sha256") or "").strip().lower()
    if not expected:
        raise ModelIntegrityError("Frozen model manifest does not declare artifact_sha256.")
    actual = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    if actual != expected:
        raise ModelIntegrityError(
            "Frozen model checksum mismatch; the artifact was not deserialized."
        )
    return joblib.load(bundle_path), manifest


def read_manifest(path: str | Path | None = None) -> dict[str, Any] | None:
    target = Path(path) if path else DEFAULT_MODEL_DIR
    manifest_path = target / "model_manifest.json"
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))
