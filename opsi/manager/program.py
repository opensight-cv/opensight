from uuid import UUID, uuid4

from .manager import Manager
from .pipeline import Node, Pipeline


class Program:
    def __init__(self):
        self.manager = Manager()
        self.pipeline = Pipeline()

    def create_node(self, func_type: str, uuid: UUID = None) -> Node:
        if uuid is None:
            uuid = uuid4()

        func = self.manager.funcs[func_type]

        return self.pipeline.create_node(func, uuid)
