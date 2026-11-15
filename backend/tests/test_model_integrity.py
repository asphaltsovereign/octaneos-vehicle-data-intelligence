import pytest

from app.services.model_store import ModelIntegrityError, load_bundle, save_bundle


def test_frozen_bundle_is_verified_before_loading(tmp_path):
    saved = save_bundle({"model_version": "test"}, {"model_version": "test"}, tmp_path)
    bundle, manifest = load_bundle(tmp_path)
    assert bundle["model_version"] == "test"
    assert manifest["artifact_sha256"] == saved["sha256"]


def test_tampered_frozen_bundle_is_rejected(tmp_path):
    save_bundle({"model_version": "test"}, {"model_version": "test"}, tmp_path)
    artifact = tmp_path / "sentinel_baseline.joblib"
    artifact.write_bytes(artifact.read_bytes() + b"tampered")
    with pytest.raises(ModelIntegrityError, match="checksum mismatch"):
        load_bundle(tmp_path)
