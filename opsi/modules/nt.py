from dataclasses import dataclass

from networktables import NetworkTables

from opsi.manager.manager_schema import Function, Hook
from opsi.manager.netdict import NT_TYPES, NetworkDict
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

    # Returns the key with the specified prefix, or no prefix if the key is empty
    def prefixed_key(self, key):
        if self.settings.key == "":
            return key
        else:
            return f"{self.settings.key}-{key}"

    # Writes a dictionary of values to network tables
    def write_dict_to_path(self, value_dict):
        for key, val in value_dict.items():
            self.table[self.prefixed_key(key)] = val

    @dataclass
    class Settings:
        path: str = "/OpenSight"
        key: str = ""

    @dataclass
    class Inputs:
        val: AnyType

    def run(self, inputs):
        if inputs.val is None:  # Do not write None values to NT
            return self.Outputs()

        # If the value has a nt_serialize function, use it.
        elif hasattr(inputs.val, "nt_serialize") and callable(inputs.val.nt_serialize):
            values = inputs.val.nt_serialize()
            self.write_dict_to_path(values)

        else:  # If the value is in NT_TYPES, write it directly to the key. If this fails, the value cannot be written.
            try:
                if self.settings.key:
                    self.table[self.settings.key] = inputs.val
                else:
                    raise ValueError(
                        "Cannot write types bool, int, float, str, bytes, or lists to NT without "
                        "a key"
                    )
            except TypeError:
                raise TypeError(
                    f"Type {inputs.val.__class__.__name__} cannot be written to NT."
                )

        return self.Outputs()

    def dispose(self):
        full_path = (self.settings.path, self.settings.key)
        UndupeInstance.remove(full_path)


class GetNT(PutNT):
    def on_start(self):
        self.table = NetworkDict(self.settings.path)
        self.validate_paths()

    def validate_paths(self):
        try:
            val = self.table[self.settings.key]
        except KeyError:
            raise ValueError(f"Key {self.settings.key}  does not exist.")

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
