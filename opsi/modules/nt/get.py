from dataclasses import dataclass

from networktables import NetworkTables

from opsi.manager.manager_schema import Function, Hook
from opsi.manager.netdict import NT_TYPES, NetworkDict
from opsi.manager.types import AnyType
from opsi.util.networking import get_nt_server
from opsi.util.unduplicator import Unduplicator

from .put import PutNT

HookInstance = Hook()


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
