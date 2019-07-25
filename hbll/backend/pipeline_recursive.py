from dataclasses import dataclass

from .pipeline import Link, Node, Pipeline


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
