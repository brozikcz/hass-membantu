from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .core import DOMAIN
from .core.entity import MembantuEntity


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, add_entities: AddEntitiesCallback
) -> None:
    device = hass.data[DOMAIN][config_entry.entry_id]

    add_entities([MembantuSwitch(device, "switch")])


class MembantuSwitch(MembantuEntity, SwitchEntity):
    def internal_update(self):
        self._attr_available = True
        self._attr_is_on = self.device.client.power_state and self.device.client.busy

        if self.hass:
            self._async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self.device.toggle()

    async def async_turn_on(self, **kwargs):
        await self.device.toggle()

