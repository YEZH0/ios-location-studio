"""Simulated-location session management.

A DVT location session only lives as long as the ``LocationSimulation``
context is open: the moment the tunnel tears down, iOS snaps back to the real
GPS fix. So the whole job of this module is to hold that context open in a
background task while the web UI polls for status, and to close it cleanly
when the user asks for it (or when the requested hold time runs out).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from pymobiledevice3.remote.userspace_tunnel import UserspaceRsdTunnel
from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation

SessionState = Literal["idle", "connecting", "active", "stopping", "error"]

CONNECT_TIMEOUT = 40.0
STOP_TIMEOUT = 20.0


@dataclass
class SessionSnapshot:
    state: SessionState = "idle"
    latitude: float | None = None
    longitude: float | None = None
    started_at: float | None = None
    expires_at: float | None = None
    error: str | None = None
    revision: int = 0
    udid: str | None = None
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        now = time.time()
        remaining = None
        elapsed = None
        if self.started_at:
            elapsed = max(0.0, now - self.started_at)
        if self.expires_at:
            remaining = max(0.0, self.expires_at - now)
        return {
            "state": self.state,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "started_at": self.started_at,
            "expires_at": self.expires_at,
            "remaining": remaining,
            "elapsed": elapsed,
            "error": self.error,
            "revision": self.revision,
            "udid": self.udid,
            "message": self.message,
            "server_time": now,
        }


@dataclass
class _Control:
    """Per-run synchronisation primitives, recreated on every start."""

    stop: asyncio.Event = field(default_factory=asyncio.Event)
    ready: asyncio.Event = field(default_factory=asyncio.Event)
    closed: asyncio.Event = field(default_factory=asyncio.Event)


class SessionManager:
    """Owns at most one live DVT location session."""

    def __init__(self) -> None:
        self._snapshot = SessionSnapshot()
        self._task: asyncio.Task[None] | None = None
        self._control: _Control | None = None
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ read

    def snapshot(self) -> dict[str, Any]:
        return self._snapshot.to_dict()

    @property
    def busy(self) -> bool:
        return self._snapshot.state in ("connecting", "active", "stopping")

    # ----------------------------------------------------------------- write

    def _touch(self, **changes: Any) -> None:
        for key, value in changes.items():
            setattr(self._snapshot, key, value)
        self._snapshot.revision += 1

    async def start(
        self,
        latitude: float,
        longitude: float,
        hold: float | None,
        udid: str,
    ) -> dict[str, Any]:
        """Launch a session and block until the tunnel reports ready (or fails)."""
        async with self._lock:
            if self._task and not self._task.done():
                await self._shutdown_locked()

            control = _Control()
            self._control = control
            self._touch(
                state="connecting",
                latitude=latitude,
                longitude=longitude,
                started_at=None,
                expires_at=None,
                error=None,
                udid=udid,
                message="正在建立 DVT 隧道…",
            )
            self._task = asyncio.create_task(
                self._run(latitude, longitude, hold, udid, control),
                name="dvt-location-session",
            )

        try:
            await asyncio.wait_for(control.ready.wait(), timeout=CONNECT_TIMEOUT)
        except asyncio.TimeoutError:
            control.stop.set()
            self._touch(
                state="error",
                error="建立隧道超时：请确认 iPhone 已解锁、已信任此电脑、开发者模式已开启。",
                message="",
            )
        return self.snapshot()

    async def stop(self) -> dict[str, Any]:
        """Close the session and let iOS restore the real GPS fix."""
        async with self._lock:
            if not self._task or self._task.done():
                if self._snapshot.state != "idle":
                    self._touch(state="idle", message="", expires_at=None)
                return self.snapshot()
            await self._shutdown_locked()
        return self.snapshot()

    async def _shutdown_locked(self) -> None:
        """Signal the running task and wait for the context to unwind."""
        control = self._control
        task = self._task
        if not control or not task:
            return

        self._touch(state="stopping", message="正在恢复真实定位…")
        control.stop.set()
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=STOP_TIMEOUT)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: B014 - best effort
                pass
        self._control = None
        self._task = None

    # -------------------------------------------------------------- worker

    async def _run(
        self,
        latitude: float,
        longitude: float,
        hold: float | None,
        udid: str,
        control: _Control,
    ) -> None:
        deadline = None
        try:
            async with UserspaceRsdTunnel(serial=udid) as rsd:
                async with DvtProvider(rsd) as dvt:
                    async with LocationSimulation(dvt) as simulation:
                        await simulation.set(latitude, longitude)
                        started = time.time()
                        deadline = started + hold if hold else None
                        self._touch(
                            state="active",
                            started_at=started,
                            expires_at=deadline,
                            latitude=latitude,
                            longitude=longitude,
                            message="模拟定位已生效",
                        )
                        control.ready.set()

                        while not control.stop.is_set():
                            if deadline and time.time() >= deadline:
                                break
                            try:
                                await asyncio.wait_for(control.stop.wait(), timeout=0.5)
                            except asyncio.TimeoutError:
                                continue

                        # Best effort: tell the device to drop the simulated fix
                        # before the context closes. Even if this raises, closing
                        # the tunnel restores the real GPS on its own.
                        try:
                            await simulation.clear()
                        except Exception:  # noqa: BLE001
                            pass
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            self._touch(
                state="error",
                error=f"{type(exc).__name__}: {exc}",
                message="",
            )
            control.ready.set()
        finally:
            control.ready.set()
            control.closed.set()
            if self._snapshot.state != "error":
                self._touch(
                    state="idle",
                    message="已停止，真实定位已恢复",
                    expires_at=None,
                    started_at=None,
                )
