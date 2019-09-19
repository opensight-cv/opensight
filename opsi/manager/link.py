from dataclasses import dataclass
from typing import Any


class Link:
    def get(self):
        raise NotImplementedError


@dataclass
class NodeLink(Link):
    node: "Node"
    name: str

    def get(self):
        return getattr(self.node.run(), self.name)


@dataclass(frozen=True)
class StaticLink(Link):
    value: Any

    def get(self):
        return self.value
