import asyncio
import logging
from asyncio import sleep
from typing import Callable

from bleak import BleakClient, BLEDevice, BleakError, BaseBleakClient
from bleak_retry_connector import establish_connection

from homeassistant.core import callback

_LOGGER = logging.getLogger(__name__)


class Client:
    def __init__(self, device: BLEDevice, callback: Callable = None):
        self.device = device
        self.callback = callback

        self.client: BleakClient | None = None

        self.timer = None
        self.speed = None
        self.remain_time = None
        self.busy = False
        self.power_state = False

        self.lock_connect = asyncio.Lock()

    def start(self):
        asyncio.create_task(self._connect())

    def is_online(self):
        return self.client and self.client.is_connected

    @callback
    def _on_disconnect(self, client: BaseBleakClient):
        _LOGGER.debug("disconnect")
        self.callback()
        asyncio.create_task(self._reconnect())

    async def _reconnect(self):
        for i in range(5):
            _LOGGER.debug(f"reconnecting {i}")
            await sleep(i * 10)
            if await self._connect():
                return

    async def _connect(self):
        async with self.lock_connect:
            _LOGGER.debug("Connecting")
            try:
                if self.client is not None and self.client.is_connected:
                    _LOGGER.debug("already connected")
                    return True

                self.client = await establish_connection(
                    BleakClient,
                    self.device,
                    self.device.address,
                    disconnected_callback=self._on_disconnect,
                    max_attempts=2,
                )
                await self.client.start_notify(
                    "0000c306-0000-1000-8000-00805f9b34fb",
                    self.notification_handler,
                )
                _LOGGER.debug("connected")
                return True
            except asyncio.TimeoutError as exc:
                _LOGGER.debug("Timeout on connect", exc_info=True)
            except BleakError as exc:
                _LOGGER.debug("Error on connect", exc_info=True)
            finally:
                self.callback()
            return False

    def notification_handler(self, sender, data):
        """Simple notification handler which prints the data received."""

        # private final byte[] generateTimeSyncPoint() {
        # return generateDataPoint$default(this, new byte[]{0, 0, 0, 0}, (byte) 7, false, 4, null);
        # }

        b = data[1]
        if b == 1:
            self.power_state = data[3] == 1
            self.busy = self.power_state

        if b == 2:
            self.speed = data[3]
        if b == 4:
            self.busy = data[3] == 0 and self.power_state
        if b == 3:
            self.timer = data[3]
        if b == 7:
            if data[2] == 3:
                applied = data[3] * 60
                remain = data[4] & 127
            else:
                applied = ((data[3] << 8) | data[4]) * 60
                remain = data[5] & 127

        if b == 6:
            print(f"data: {list(data)}")
        else:
            # _LOGGER.debug(f"times: {applied} - {remain}")
            # _LOGGER.debug(f"speed: {self.speed}")
            # _LOGGER.debug(f"power state: {self.power_state}")
            # _LOGGER.debug(f"busy: {self.busy}")
            # _LOGGER.debug(f"timer: {self.timer}")
            self.callback()

    async def send_cmd(self, data):
        _LOGGER.debug(f"data: {data}, state: {self.client.is_connected}")
        if not self.client.is_connected:
            await self._connect()

        data_as_bytes = bytearray.fromhex(data)
        await self.client.write_gatt_char(
            "0000c304-0000-1000-8000-00805f9b34fb",
            data_as_bytes,
            False,
        )
