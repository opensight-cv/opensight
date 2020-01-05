from dataclasses import dataclass

from opsi.manager.manager_schema import Function
from opsi.manager.netdict import NetworkDict
from opsi.manager.types import AnyType
from opsi.util.cv import Point
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
        val: Point

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
