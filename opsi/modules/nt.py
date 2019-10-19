from dataclasses import dataclass

from networktables import NetworkTables

from opsi.manager.manager_schema import Function

__package__ = "demo.nt"
__version__ = "0.123"


class PutInteger(Function):
    def on_start(self):
        self.table = NetworkTables.getTable("SmartDashboard")

    @dataclass
    class Settings:
        key: str

    @dataclass
    class Inputs:
        val: int

    def run(self, inputs):
        self.table.putNumber(self.settings.key, inputs.val)


class PutString(Function):
    def on_start(self):
        self.table = NetworkTables.getTable("SmartDashboard")

    @dataclass
    class Settings:
        key: str

    @dataclass
    class Inputs:
        val: int

    def run(self, inputs):
        self.table.putString(self.settings.key, inputs.val)


class PutCoordinate(Function):
    def on_start(self):
        self.table = NetworkTables.getTable("SmartDashboard")

    @dataclass
    class Settings:
        key: str

    @dataclass
    class Inputs:
        val: ()

    def run(self, inputs):
        xkey = self.settings.key + "-x"
        ykey = self.settings.key + "-y"
        x, y = inputs.val[0], inputs.val[1]
        self.table.putNumber(xkey, x)
        self.table.putNumber(ykey, y)
