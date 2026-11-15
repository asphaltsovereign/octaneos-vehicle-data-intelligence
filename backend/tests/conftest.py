"""Original laboratory regression tests run in explicit development DEMO mode."""
import pytest
@pytest.fixture(autouse=True)
def explicit_test_mode(monkeypatch):
    monkeypatch.setenv('OCTANE_ENV','development')
    monkeypatch.setenv('OCTANE_DEMO','1')
