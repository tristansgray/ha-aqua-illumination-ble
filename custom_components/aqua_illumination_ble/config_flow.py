"""Config flow: Bluetooth discovery or pick from discovered devices, then identity check."""
from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from . import DOMAIN, ERRORS, async_read_device_info, is_tested
from .protocol import SERVICE


class AquaIlluminationConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._found: dict[str, str] = {}
        self._data: dict[str, str] = {}

    async def async_step_bluetooth(self, info: BluetoothServiceInfoBleak) -> ConfigFlowResult:
        await self.async_set_unique_id(info.address)
        self._abort_if_unique_id_configured()
        self._found = {info.address: f"{info.name} ({info.address})"}
        self.context["title_placeholders"] = {"name": info.name}
        return await self.async_step_user()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            try:
                info = await async_read_device_info(self.hass, address)
            except ERRORS:
                errors["base"] = "cannot_connect"
            else:
                self._data = {CONF_ADDRESS: address, **info}
                if is_tested(info["model"], info["firmware"]):
                    return self.async_create_entry(title="Axis 40", data=self._data)
                return await self.async_step_untested()

        if not self._found:
            configured = self._async_current_ids()
            for info in async_discovered_service_info(self.hass):
                if info.address not in configured and (
                    info.name == "MOBIUS" or SERVICE in info.service_uuids
                ):
                    self._found[info.address] = f"{info.name} ({info.address})"
        if not self._found:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS): vol.In(self._found)}),
            errors=errors,
        )

    async def async_step_untested(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Device is not a verified model/firmware: require explicit acceptance."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input["accept"]:
                return self.async_create_entry(
                    title=f"AI {self._data['model']}", data=self._data
                )
            errors["base"] = "must_accept"
        return self.async_show_form(
            step_id="untested",
            data_schema=vol.Schema({vol.Required("accept", default=False): bool}),
            description_placeholders={
                "model": self._data["model"],
                "firmware": self._data["firmware"],
            },
            errors=errors,
        )
