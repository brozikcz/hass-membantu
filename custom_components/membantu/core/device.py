from datetime import datetime, timezone
from typing import Callable

from bleak import BLEDevice, AdvertisementData

from .client import Client


class Device:
    def __init__(self, name: str, device: BLEDevice, advertisment: AdvertisementData):
        self.name = name

        self.client = Client(device, self.set_connected)

        self.conn_info = {"mac": device.address}

        self.product = None
        self.values = None
        self.updates_connect: list = []
        self.updates_product: list = []

        self.update_ble(advertisment)
        self.client.start()

    @property
    def mac(self) -> str:
        return self.client.device.address

    def register_update(self, attr: str, handler: Callable):
        if attr == "product":
            return
        elif attr == "connection" or attr == "make":
            self.updates_connect.append(handler)
        else:
            self.updates_product.append(handler)

    def update_ble(self, advertisment: AdvertisementData):
        self.conn_info["last_seen"] = datetime.now(timezone.utc)
        self.conn_info["rssi"] = advertisment.rssi

        for handler in self.updates_connect:
            handler()

    def set_connected(self):

        for handler in self.updates_connect:
            handler()

        for handler in self.updates_product:
            handler()

    async def select_option(self, attr: str, option: str):
        await self.client.send_cmd(f"AA0301{option}DD0D0A")

    async def set_value(self, attr: str, value: int):
        await self.client.send_cmd(f"AA0201{f"0{value}" if value < 10 else f"0A"}DD0D0A")

    async def toggle(self):
        if not self.client.power_state:
            data = "AA010101DD0D0A"
        else:
            data = "AA040101DD0D0A" if (self.client.busy == True) else "AA040100DD0D0A"

        await self.client.send_cmd(data)
