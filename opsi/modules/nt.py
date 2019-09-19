import time
from dataclasses import dataclass

from networktables import NetworkTables

from opsi.manager.manager_schema import Function


class InitializeNT(Function):
    @dataclass
    class Settings:
        teamnum: int

    def run(self, inputs):
        mDNS = f"roboRIO-{self.settings.teamnum}-FRC.local"
        NetworkTables.initialize(server=mDNS)


class PutInteger(Function):
    def on_start(self):
        self.table = NetworkTables.getTable("SmartDashboard")

    @dataclass
    class Settings:
        name: str

    @dataclass
    class Inputs:
        val: int

    def run(self, inputs):
        self.table.putInt(self.settings.name, inputs.val)
