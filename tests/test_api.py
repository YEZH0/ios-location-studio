"""Smoke tests that never touch a real device."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ios_location_studio import server
from ios_location_studio.device import Inventory
from ios_location_studio.presets import PRESETS


@pytest.fixture()
def client(monkeypatch):
    async def fake_list_connected() -> Inventory:
        return Inventory(connected=False, devices=[], error=None)

    monkeypatch.setattr(server, "list_connected", fake_list_connected)
    app = server.create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_presets_are_well_formed():
    assert len(PRESETS) >= 10
    ids = set()
    for preset in PRESETS:
        assert preset["id"] not in ids
        ids.add(preset["id"])
        assert -90 <= preset["latitude"] <= 90
        assert -180 <= preset["longitude"] <= 180
        assert preset["name"]


def test_status_shape(client):
    payload = client.get("/api/status").json()
    assert set(payload) == {"version", "device", "session"}
    assert payload["device"]["connected"] is False
    assert payload["session"]["state"] == "idle"
    assert payload["session"]["remaining"] is None


def test_simulate_without_device_returns_conflict(client):
    response = client.post(
        "/api/simulate",
        json={"latitude": 40.416863, "longitude": -3.703876, "hold_seconds": 60},
    )
    assert response.status_code == 409
    assert "iPhone" in response.json()["detail"]


def test_simulate_rejects_out_of_range(client):
    response = client.post("/api/simulate", json={"latitude": 91, "longitude": 0})
    assert response.status_code == 422


def test_index_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Location Studio" in response.text
