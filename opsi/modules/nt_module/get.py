from dataclasses import dataclass

from opsi.manager.manager_schema import Hook
from opsi.manager.netdict import NT_AVAIL, NetworkDict
from opsi.manager.types import AnyType

from .put import PutNT

if not NT_AVAIL:
    raise ImportError("NetworkTables is not available")

HookInstance = Hook()


class GetNT(PutNT):
    def on_start(self):
        self.table = NetworkDict(self.settings.path)

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
