import asyncio
import logging
import time
from typing import Callable

from bleak import BleakClient, BLEDevice, BleakError
from bleak_retry_connector import establish_connection

_LOGGER = logging.getLogger(__name__)

ACTIVE_TIME = 120
COMMAND_TIME = 15


class Client:
    def __init__(self, device: BLEDevice, callback: Callable = None):
        self.device = device
        self.callback = callback

        self.client: BleakClient | None = None

        self.ping_future: asyncio.Future | None = None
        self.ping_task: asyncio.Task | None = None
        self.ping_time = 0

        self.send_data = None
        self.send_time = 0

        self.timer = None
        self.speed = None
        self.remain_time = None
        self.busy = False
        self.power_state = False

    def start(self):
        asyncio.create_task(self._loop())

    def is_online(self):
        return self.client and self.client.is_connected

    def _on_disconnect(self):
        _LOGGER.debug("disconnect")
        # self.callback(False)
        # asyncio.create_task(self._loop())

    async def _loop(self):
        _LOGGER.debug("Connecting")
        try:
            self.client = await establish_connection(
                BleakClient, self.device, self.device.address, disconnected_callback=self._on_disconnect()
            )
            self.callback()
            await self.client.start_notify(
                "0000c306-0000-1000-8000-00805f9b34fb",
                self.notification_handler,
            )
        except asyncio.TimeoutError as exc:
            _LOGGER.debug("Timeout on connect", exc_info=True)
            raise exc
        except BleakError as exc:
            _LOGGER.debug("Error on connect", exc_info=True)
            raise exc

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
            print(f"speed: {self.speed}")
        if b == 4:
            self.busy = data[3] == 0 and self.power_state
        if b == 7:
            if data[2] == 3:
                applied = data[3] * 60
                remain = data[4]
            else:
                applied = (data[3] << 8| data[4]) * 60
                remain = data[5]
            print(f"times: {applied} - {remain}")

        print(f"power state: {self.power_state}")
        print(f"busy: {self.busy}")
        print(f"data: {list(data)}")
        self.callback()

    def ping(self):
        self.ping_time = time.time() + ACTIVE_TIME

        if not self.ping_task:
            self.ping_task = asyncio.create_task(self._ping_loop())

    def send(self, data: bytes):
        # if send loop active - we change sending data
        self.send_time = time.time() + COMMAND_TIME
        self.send_data = data

        self.ping()

        if self.ping_future:
            self.ping_future.cancel()

    async def _ping_loop(self):
        loop = asyncio.get_event_loop()

        while time.time() < self.ping_time:
            try:
                self.client = await establish_connection(
                    BleakClient, self.device, self.device.address
                )
                if self.callback:
                    self.callback(True)

                # heartbeat loop
                while time.time() < self.ping_time:
                    # important dummy read for keep connection
                    data = await self.client.read_gatt_char(
                        "5a401531-ab2e-2548-c435-08c300000710"
                    )
                    key = data[0]

                    if self.send_data:
                        if time.time() < self.send_time:
                            await self.client.write_gatt_char(
                                "0000c304-0000-1000-8000-00805f9b34fb",
                                data=encrypt(self.send_data, key),
                                response=True,
                            )
                        self.send_data = None

                    # asyncio.sleep(10) with cancel
                    self.ping_future = loop.create_future()
                    loop.call_later(10, self.ping_future.cancel)
                    try:
                        await self.ping_future
                    except asyncio.CancelledError:
                        pass

                await self.client.disconnect()
            except TimeoutError:
                pass
            except BleakError as e:
                _LOGGER.debug("ping error", exc_info=e)
            except Exception as e:
                _LOGGER.warning("ping error", exc_info=e)
            finally:
                self.client = None
                if self.callback:
                    self.callback(False)
                await asyncio.sleep(1)

        self.ping_task = None

    async def send_cmd(self, data):
        print(f"data: {data}, state: {self.client.is_connected}")

        data_as_bytes = bytearray.fromhex(data)
        await self.client.write_gatt_char(
            "0000c304-0000-1000-8000-00805f9b34fb",
            data_as_bytes,
            False,
        )
