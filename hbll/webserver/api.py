from fastapi import FastAPI

from ..backend.program import Program
from .schema import NodeTreeN, SchemaF
from .serialize import *

__all__ = ("export_manager", "export_nodetree", "import_nodetree")


class Api:
    def __init__(self, parent_app, program: Program, prefix="/api"):
        self.program = program

        self.app = FastAPI(openapi_prefix=prefix)

        self.app.get("/funcs", response_model=SchemaF)(self.read_funcs)
        self.app.get("/nodes", response_model=NodeTreeN)(self.read_nodes)
        self.app.post("/nodes")(self.save_nodes)

        parent_app.mount(prefix, self.app)

    def read_funcs(self) -> SchemaF:
        return export_manager(self.program.manager)

    def read_nodes(self) -> NodeTreeN:
        return export_nodetree(self.program.pipeline)

    def save_nodes(self, *, nodetree: NodeTreeN):
        return import_nodetree(self.program.pipeline, nodetree)
