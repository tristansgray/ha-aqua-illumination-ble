"""Aqua Illumination (AI) Mobius BLE devices. Tested: Axis 40 pump."""
import asyncio
from datetime import timedelta
import logging

from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .protocol import DEV_INFO, Axis

_LOGGER = logging.getLogger(__name__)
DOMAIN = "aqua_illumination"
PLATFORMS = [Platform.BUTTON, Platform.SENSOR]
ERRORS = (BleakError, TimeoutError, ValueError, RuntimeError)
# (model string, firmware major.minor) verified on hardware. The Axis 40 reports "Nero 5".
TESTED = {("Nero 5", "2.3")}


def is_tested(model: str, firmware: str) -> bool:
    return (model, ".".join(firmware.split(".")[:2])) in TESTED


async def async_read_device_info(hass: HomeAssistant, address: str) -> dict[str, str]:
    """Connect once and read the standard Device Information strings."""
    ble = bluetooth.async_ble_device_from_address(hass, address, connectable=True)
    if ble is None:
        raise BleakError("device not advertising (out of range, or myAI app connected)")
    client = await establish_connection(BleakClientWithServiceCache, ble, address)
    try:
        return {
            k: (await client.read_gatt_char(u)).decode(errors="replace").strip("\x00 ")
            for k, u in DEV_INFO.items()
        }
    finally:
        await client.disconnect()


class AxisCoordinator(DataUpdateCoordinator[tuple[int, int]]):
    """Holds (flow in 0.1% steps, rpm)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=timedelta(seconds=60)
        )
        self.address: str = entry.data[CONF_ADDRESS]
        self._lock = asyncio.Lock()

    async def _session(self, payload: bytes | None = None) -> tuple[int, int]:
        # ponytail: connect per poll, not held open; the pump takes one client, so the
        # myAI app can still get in between polls. Hold the connection if 60 s is too slow.
        ble = bluetooth.async_ble_device_from_address(self.hass, self.address, connectable=True)
        if ble is None:
            raise BleakError("pump not advertising (out of range, or myAI app connected)")
        async with self._lock:
            client = await establish_connection(BleakClientWithServiceCache, ble, self.address)
            try:
                axis = Axis(client)
                await axis.start()
                if payload:
                    await axis.write(payload)
                    await asyncio.sleep(5)  # let flow/RPM settle before reading back
                return await axis.state()
            finally:
                await client.disconnect()

    async def _async_update_data(self) -> tuple[int, int]:
        try:
            return await self._session()
        except ERRORS as err:
            raise UpdateFailed(str(err)) from err

    async def async_command(self, payload: bytes) -> None:
        try:
            self.async_set_updated_data(await self._session(payload))
        except ERRORS as err:
            raise HomeAssistantError(f"Axis command failed: {err}") from err


class AxisEntity(CoordinatorEntity[AxisCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: AxisCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_{key}"
        data = coordinator.config_entry.data
        model, firmware = data.get("model", ""), data.get("firmware", "")
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, coordinator.address)},
            name=coordinator.config_entry.title,
            manufacturer="Aqua Illumination",
            model="Axis 40" if is_tested(model, firmware) else model,
            sw_version=firmware or None,
            serial_number=data.get("serial"),
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = AxisCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
