from homeassistant.components.button import ButtonEntity

from . import AxisEntity
from .protocol import FEED, OFF, SCHEDULE, TIMED

BUTTONS = {
    "schedule": ("Resume schedule", SCHEDULE),
    "feed": ("Feed", FEED),  # runs at the Feed Mode speed set in the myAI app
    "timed": ("Full flow 1 hour", TIMED),
    "off": ("Off", OFF),  # stays off until Resume schedule
}


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    async_add_entities(AxisButton(entry.runtime_data, key) for key in BUTTONS)


class AxisButton(AxisEntity, ButtonEntity):
    def __init__(self, coordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self._attr_name, self._payload = BUTTONS[key]

    async def async_press(self) -> None:
        await self.coordinator.async_command(self._payload)
