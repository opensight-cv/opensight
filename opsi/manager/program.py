from uuid import UUID, uuid4

from .manager import Manager
from .pipeline import Node
from .pipeline_recursive import RecursivePipeline


class Program:
    def __init__(self):
        self.manager = Manager()
        self.pipeline = RecursivePipeline()

    def create_node(self, func_type: str, id: UUID = None) -> Node:
        if id is None:
            id = uuid4()

        func = self.manager.funcs[func_type]

        return self.pipeline.create_node(func, id)
