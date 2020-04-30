from dataclasses import dataclass

from opsi.manager.manager_schema import Function
from opsi.manager.netdict import NetworkDict
from opsi.manager.types import AnyType
from opsi.util.unduplicator import Unduplicator

UndupeInstance = Unduplicator()


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
