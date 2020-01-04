from dataclasses import dataclass

from networktables import NetworkTables

from opsi.manager.manager_schema import Function, Hook
from opsi.manager.netdict import NetworkDict
from opsi.manager.types import AnyType
from opsi.util.networking import get_nt_server
from opsi.util.unduplicator import Unduplicator

__package__ = "opsi.nt"
__version__ = "0.123"


class Manager:
    def __init__(self):
        self.keys = set()

    @classmethod
    def make_path(cls, settings):
        return settings.path + "/" + settings.key

    def add(self, settings):
        path = self.make_path(settings)

        if path in self.keys:
            raise ValueError("Cannot have duplicate path")

        self.keys.add(path)

    def dispose(self, settings):
        self.keys.discard(self.make_path(settings))


UndupeInstance = Unduplicator()
HookInstance = Hook(visible=False)


def init_networktables():
    network = HookInstance.persist.network
    if network.nt_enabled:
        if network.nt_client:
            addr = get_nt_server(network)
            NetworkTables.startClient(addr)
        else:
            NetworkTables.startServer()


def deinit_networktables():
    if HookInstance.persist.network.nt_enabled:
        NetworkTables.shutdown()


HookInstance.add_listener("startup", init_networktables)
HookInstance.add_listener("shutdown", deinit_networktables)


class PutNT(Function):
    has_sideeffect = True

    @classmethod
    def validate_settings(cls, settings):
        settings.path = settings.path.strip()
        settings.key = settings.key.strip()

        if not settings.path.startswith("/"):
            raise ValueError("You must have an absolute that starts with '/'")

        if not settings.key:
            raise ValueError("Key cannot be empty")

        if "/" in settings.key:
            raise ValueError("Key cannot have '/' in it")

        return settings

    def on_start(self):
        self.validate_paths()
        self.table = NetworkDict(self.settings.path)

    def validate_paths(self):
        fullPath = (self.settings.path, self.settings.key)
        if not UndupeInstance.add(fullPath):
            raise ValueError("Cannot have duplicate NetworkTables paths")

    @dataclass
    class Settings:
        path: str = "/OpenSight"
        key: str = ""

    @dataclass
    class Inputs:
        val: AnyType

    def run(self, inputs):
        self.table[self.settings.key] = inputs.val

        return self.Outputs()

    def dispose(self):
        fullPath = (self.settings.path, self.settings.key)
        UndupeInstance.remove(fullPath)


class PutCoordinate(PutNT):
    def validate_paths(self):
        x = (self.settings.path, f"{self.settings.key}-x")
        y = (self.settings.path, f"{self.settings.key}-y")
        xSuccess = UndupeInstance.add(x)
        ySuccess = UndupeInstance.add(y)
        if not xSuccess or not ySuccess:
            raise ValueError("Cannot have duplicate NetworkTables paths")

    @dataclass
    class Inputs:
        val: tuple()

    def run(self, inputs):
        if inputs.val:
            x, y, *_ = inputs.val

            self.table[f"{self.settings.key}-x"] = x
            self.table[f"{self.settings.key}-y"] = y

        return self.Outputs()

    def dispose(self):
        x = (self.settings.path, f"{self.settings.key}-x")
        y = (self.settings.path, f"{self.settings.key}-y")
        UndupeInstance.remove(x)
        UndupeInstance.remove(y)


class GetNT(PutNT):
    def on_start(self):
        self.table = NetworkDict(self.settings.path)
        self.validate_paths()

    def validate_paths(self):
        try:
            val = self.table[self.settings.key]
        except KeyError:
            raise ValueError(f"Key does {self.settings.key} not exist.")

    @dataclass
    class Inputs:
        pass

    @dataclass
    class Outputs:
        val: AnyType = None

    def run(self, inputs):
        val = self.table.get(self.settings.key, None)
        if val is None:
            HookInstance.cancel_output("val")
            return self.Outputs()

        return self.Outputs(val=val)
