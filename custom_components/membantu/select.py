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
        self._attr_current_option = "∞" if (self.device.client.timer is None or self.device.client.timer >= 4) else str((self.device.client.timer + 1) * 15)
        self._attr_options = ["15", "30", "45", "60", "∞"]
        self._attr_available = True

        if self.hass:
            self._async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        if option == "∞":
            value = 4
        else:
            value = max((int(option) / 15) - 1, 0)
        await self.device.select_option(self.attr, f"0{int(value)}")
        self._attr_current_option = option
        self._async_write_ha_state()
