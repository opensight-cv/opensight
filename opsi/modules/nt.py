from dataclasses import dataclass

from opsi.manager.manager_schema import Function
from opsi.manager.netdict import NetworkDict
from opsi.manager.types import AnyType

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


ManagerInstance = Manager()


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
        ManagerInstance.add(self.settings)
        self.table = NetworkDict(self.settings.path)

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
        ManagerInstance.dispose(self.settings)


class PutCoordinate(PutNT):
    @dataclass
    class Inputs:
        val: tuple()

    def run(self, inputs):
        x, y, *_ = inputs.val

        self.table[f"{self.settings.key}-x"] = x
        self.table[f"{self.settings.key}-y"] = y

        return self.Outputs()
