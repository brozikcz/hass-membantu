from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN
from .core.entity import MembantuEntity


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    device = hass.data[DOMAIN][config_entry.entry_id]

    add_entities([MembantuNumber(device, "speed")])


class MembantuNumber(MembantuEntity, NumberEntity):
    def internal_update(self):

        self._attr_available = True
        self._attr_native_min_value = 0
        self._attr_native_max_value = 10
        self._attr_native_step = 1
        self._attr_native_value = self.device.client.speed or 0

        if self.hass:
            self._async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        await self.device.set_value(self.attr, int(value))
        self._attr_native_value = int(value)
        self._async_write_ha_state()
