from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN
from .core.entity import MembantuEntity


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, add_entities: AddEntitiesCallback
):
    device = hass.data[DOMAIN][config_entry.entry_id]

    add_entities([MembantuSelect(device, "timer")])


class MembantuSelect(MembantuEntity, SelectEntity):
    def internal_update(self):
        self._attr_current_option = self.device.client.timer or "∞"
        self._attr_options = ["15", "30", "∞"]
        self._attr_available = True

        if self.hass:
            self._async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        await self.device.select_option(self.attr, option)
        self._attr_current_option = option
        self._async_write_ha_state()
