"""Config flow: tested device is added directly; untested device needs explicit acceptance."""
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.const import CONF_ADDRESS
from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.aqua_illumination import DOMAIN

ADDR = "AA:BB:CC:DD:EE:FF"
FLOW = "custom_components.aqua_illumination.config_flow"


class Info:  # stand-in for BluetoothServiceInfoBleak
    address, name, service_uuids = ADDR, "MOBIUS", []


@pytest.fixture(autouse=True)
def _enable(enable_custom_integrations):
    yield


async def _pick(hass, model, firmware):
    with patch(f"{FLOW}.async_discovered_service_info", return_value=[Info()]):
        r = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert r["step_id"] == "user"
    info = {"manufacturer": "AI", "model": model, "firmware": firmware, "serial": "X"}
    with patch(f"{FLOW}.async_read_device_info", return_value=info), patch(
        "custom_components.aqua_illumination.async_setup_entry", return_value=True
    ):
        return await hass.config_entries.flow.async_configure(r["flow_id"], {CONF_ADDRESS: ADDR})


async def test_tested_device(hass):
    r = await _pick(hass, "Nero 5", "2.3.15")
    assert r["type"] is FlowResultType.CREATE_ENTRY
    assert r["title"] == "Axis 40" and r["data"]["model"] == "Nero 5"


async def test_untested_device_requires_accept(hass):
    r = await _pick(hass, "Radion", "1.0.0")
    assert r["step_id"] == "untested"
    with patch("custom_components.aqua_illumination.async_setup_entry", return_value=True):
        r = await hass.config_entries.flow.async_configure(r["flow_id"], {"accept": False})
        assert r["errors"] == {"base": "must_accept"}
        r = await hass.config_entries.flow.async_configure(r["flow_id"], {"accept": True})
    assert r["type"] is FlowResultType.CREATE_ENTRY and r["title"] == "AI Radion"


async def test_cannot_connect(hass):
    with patch(f"{FLOW}.async_discovered_service_info", return_value=[Info()]):
        r = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        with patch(f"{FLOW}.async_read_device_info", side_effect=TimeoutError):
            r = await hass.config_entries.flow.async_configure(r["flow_id"], {CONF_ADDRESS: ADDR})
    assert r["errors"] == {"base": "cannot_connect"}
