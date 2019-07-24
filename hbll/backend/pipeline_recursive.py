from .pipeline import Node, Link, Pipeline
from dataclasses import dataclass


@dataclass
class RecursiveLink(Link):
    node: Node
    name: str

    def run(self):
        return getattr(self.node.run(), self.name)


class RecursivePipeline(Pipeline):
    def _run(self):
        for id in self.entrynodes:
            self.nodes[id].run()

    def _create_link(self, node, name, conn):
        return RecursiveLink(conn.node, conn.name)
