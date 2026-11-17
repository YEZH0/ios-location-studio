"""Smoke tests that never touch a real device."""

from __future__ import annotations

from urllib.parse import unquote

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
    assert set(payload) == {"version", "brand", "device", "session"}
    assert payload["device"]["connected"] is False
    assert payload["session"]["state"] == "idle"
    assert payload["session"]["remaining"] is None


def test_brand_is_served(client):
    brand = client.get("/api/brand").json()
    assert brand["brand"] == "欧耶哥爱数码"
    assert brand["tutorial_keyword"] == "欧耶哥爱数码"
    assert brand["homepage"].startswith("https://github.com/")
    assert len(brand["channels"]) >= 2
    assert brand["promo_image"].endswith(".jpg")


def test_disclaimer_is_served(client):
    brand = client.get("/api/brand").json()
    assert brand["disclaimer_title"] == "免责声明"
    assert len(brand["disclaimer"]) == 4
    joined = "".join(brand["disclaimer"])
    # The clauses that actually carry legal weight must survive edits.
    assert "仅面向 iOS 开发者做定位相关功能技术研究" in joined
    assert "高血压通知" in joined
    assert "考勤打卡" in joined and "游戏作弊" in joined
    assert "作者不对违规使用承担任何责任" in joined


@pytest.mark.parametrize("name", ["follow-banner.jpg"])
def test_brand_assets_are_shipped(client, name):
    response = client.get(f"/static/assets/{name}")
    assert response.status_code == 200
    assert len(response.content) > 40000


def test_provenance_headers(client):
    response = client.get("/api/health")
    assert response.headers["X-Brand"] == "ouyege-aishuma"
    assert unquote(response.headers["X-Brand-Name"]) == "欧耶哥爱数码"
    assert "github.com" in response.headers["X-Author"]
    assert "research-and-education-only" in response.headers["X-Usage-Policy"]


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
