import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .core import DOMAIN
from .core.device import Device

PLATFORMS = ["binary_sensor", "switch", "number", "select"]
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    devices = hass.data.setdefault(DOMAIN, {})

    @callback
    def update_ble(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        _LOGGER.debug(f"update ble {service_info} {change}")

        if device := devices.get(entry.entry_id):
            device.update_ble(service_info)
            return

        devices[entry.entry_id] = Device(
            entry.title, service_info.device, service_info.advertisement
        )

        hass.create_task(
            hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        )

    @callback
    def _unavailable_callback(service_info: bluetooth.BluetoothServiceInfoBleak) -> None:
        _LOGGER.debug(f"is no longer seen {service_info}")
        if device := devices.get(entry.entry_id):
            device.update_ble(service_info)

    entry.async_on_unload(
        bluetooth.async_track_unavailable(hass, _unavailable_callback, entry.data["mac"], connectable=True)
    )

    # https://developers.home-assistant.io/docs/core/bluetooth/api/
    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            update_ble,
            {"address": entry.data["mac"]},
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    if entry.entry_id in hass.data[DOMAIN]:
        await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return True
