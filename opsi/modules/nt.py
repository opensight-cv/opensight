from dataclasses import dataclass

from networktables import NetworkTables

from opsi.manager.manager_schema import Function

class InitializeNT(Function):
    @dataclass
    class Settings:
        teamnum: int
        client: bool
        staticIP: bool

    def run(self, inputs):
        if not self.settings.client:
            NetworkTables.initialize()
        else:
            static = f"10.{self.settings.teamnum[:2]}.{self.settings.teamnum[:-2]}.2"
            mDNS = f"roboRIO-{self.settings.teamnum}-FRC.local"
            if self.settings.staticIP:
                NetworkTables.initialize(server=static)
            else:
                NetworkTables.initialize(server=mDNS)


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
