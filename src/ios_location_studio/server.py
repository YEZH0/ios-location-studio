"""FastAPI application: JSON API plus the single-page control panel."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .brand import AUTHOR, BRAND, BRAND_SLUG, HOMEPAGE, brand_payload
from .device import Inventory, list_connected
from .presets import PRESETS
from .session import SessionManager

WEB_DIR = Path(__file__).parent / "web"
DEVICE_REFRESH_SECONDS = 8.0


class SimulateRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 longitude")
    hold_seconds: float | None = Field(
        default=None,
        ge=1.0,
        le=86400.0,
        description="How long to keep the fix active; null means until stopped manually.",
    )
    udid: str | None = Field(default=None, description="Target device; first device when omitted.")


class DeviceCache:
    """Keeps device metadata warm without hammering usbmux on every poll."""

    def __init__(self) -> None:
        self.inventory = Inventory()
        self.updated_at = 0.0
        self._lock = asyncio.Lock()

    async def refresh(self, force: bool = False) -> Inventory:
        if not force and (time.monotonic() - self.updated_at) < DEVICE_REFRESH_SECONDS:
            return self.inventory
        async with self._lock:
            if not force and (time.monotonic() - self.updated_at) < DEVICE_REFRESH_SECONDS:
                return self.inventory
            self.inventory = await list_connected()
            self.updated_at = time.monotonic()
            return self.inventory


def create_app() -> FastAPI:
    manager = SessionManager()
    cache = DeviceCache()

    async def refresher() -> None:
        while True:
            try:
                await cache.refresh(force=True)
            except Exception:  # noqa: BLE001 - never let the poller die
                pass
            await asyncio.sleep(DEVICE_REFRESH_SECONDS)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = asyncio.create_task(refresher(), name="device-refresher")
        try:
            yield
        finally:
            task.cancel()
            try:
                await manager.stop()
            except Exception:  # noqa: BLE001
                pass

    app = FastAPI(
        title="iOS Location Studio",
        version=__version__,
        description="Simulate iPhone location over Apple's DVT developer channel.",
        lifespan=lifespan,
    )
    app.state.manager = manager
    app.state.cache = cache

    @app.middleware("http")
    async def stamp_origin(request, call_next):
        """Attach provenance headers to every response.

        Anyone inspecting the traffic - or wiring this API into their own
        front-end - still sees where the backend came from.

        HTTP header values are latin-1 only, so the Chinese brand name is
        percent-encoded alongside an ASCII slug that can be compared directly.
        """
        response = await call_next(request)
        response.headers["X-Brand"] = BRAND_SLUG
        response.headers["X-Brand-Name"] = quote(BRAND, safe="")
        response.headers["X-Author"] = f"{AUTHOR} <{HOMEPAGE}>"
        return response

    if WEB_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(
            WEB_DIR / "index.html",
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {"ok": True, "version": __version__, "brand": brand_payload()}

    @app.get("/api/brand")
    async def brand() -> dict[str, Any]:
        return brand_payload()

    @app.get("/api/presets")
    async def presets() -> dict[str, Any]:
        return {"presets": PRESETS}

    @app.get("/api/devices")
    async def devices() -> dict[str, Any]:
        inventory = await cache.refresh()
        return inventory.to_dict()

    @app.get("/api/status")
    async def status() -> dict[str, Any]:
        inventory = await cache.refresh()
        return {
            "version": __version__,
            "brand": brand_payload(),
            "device": inventory.to_dict(),
            "session": manager.snapshot(),
        }

    @app.post("/api/simulate")
    async def simulate(payload: SimulateRequest) -> dict[str, Any]:
        inventory = await cache.refresh()
        if not inventory.devices:
            raise HTTPException(
                status_code=409,
                detail="未检测到 USB 连接的 iPhone。请解锁设备并信任此电脑后重试。",
            )

        udid = payload.udid or inventory.devices[0].udid
        if payload.udid and payload.udid not in {d.udid for d in inventory.devices}:
            raise HTTPException(status_code=404, detail=f"设备未连接: {payload.udid}")

        snapshot = await manager.start(
            latitude=payload.latitude,
            longitude=payload.longitude,
            hold=payload.hold_seconds,
            udid=udid,
        )
        if snapshot["state"] == "error":
            return JSONResponse(status_code=502, content={"session": snapshot})
        return {"session": snapshot}

    @app.post("/api/stop")
    async def stop() -> dict[str, Any]:
        return {"session": await manager.stop()}

    return app


app = create_app()
