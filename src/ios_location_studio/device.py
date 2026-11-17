"""Device discovery helpers.

Wraps the two things we need from ``pymobiledevice3``: an inventory of the
USB-connected devices, and a single UDID to open the DVT channel against.
Every call is defensive - a missing device or a partially supported lockdown
key must never take the web server down.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.usbmux import list_devices

# Keys we try to lift out of the lockdown record. Anything missing is left as
# None so the UI can render a placeholder instead of blowing up.
_LOCKDOWN_KEYS = {
    "DeviceName": "name",
    "ProductVersion": "ios_version",
    "BuildVersion": "build",
    "ProductType": "model",
}


@dataclass
class DeviceInfo:
    udid: str
    name: str | None = None
    ios_version: str | None = None
    build: str | None = None
    model: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Inventory:
    connected: bool = False
    devices: list[DeviceInfo] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "devices": [d.to_dict() for d in self.devices],
            "error": self.error,
        }


async def _read_lockdown(serial: str) -> dict[str, str | None]:
    """Pull display metadata out of the lockdown service for one device."""
    values: dict[str, str | None] = {}
    try:
        async with await create_using_usbmux(serial=serial) as lockdown:
            record = await lockdown.get_value()
            if isinstance(record, dict):
                for raw_key, attr in _LOCKDOWN_KEYS.items():
                    value = record.get(raw_key)
                    values[attr] = str(value) if value is not None else None
    except Exception:  # noqa: BLE001 - metadata is strictly cosmetic
        pass
    return values


async def list_connected() -> Inventory:
    """Enumerate USB devices and enrich each with lockdown metadata."""
    try:
        raw_devices = await list_devices()
    except Exception as exc:  # noqa: BLE001
        return Inventory(connected=False, error=f"{type(exc).__name__}: {exc}")

    devices: list[DeviceInfo] = []
    for raw in raw_devices:
        serial = getattr(raw, "serial", None)
        if not serial:
            continue
        info = DeviceInfo(udid=serial)
        meta = await _read_lockdown(serial)
        info.name = meta.get("name")
        info.ios_version = meta.get("ios_version")
        info.build = meta.get("build")
        info.model = meta.get("model")
        devices.append(info)

    return Inventory(connected=bool(devices), devices=devices)


async def first_udid() -> str | None:
    """Convenience helper: the UDID a session should attach to."""
    inventory = await list_connected()
    if inventory.devices:
        return inventory.devices[0].udid
    return None
