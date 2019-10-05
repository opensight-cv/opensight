from fastapi import FastAPI, File, UploadFile

from ..backend.upgrade import upgrade_opsi
from .schema import NodeTreeN, SchemaF
from .serialize import *


class Api:
    def __init__(self, parent_app, program, prefix="/api"):
        self.program = program

        self.app = FastAPI(openapi_prefix=prefix)

        self.app.get("/funcs", response_model=SchemaF)(self.read_funcs)
        self.app.get("/nodes", response_model=NodeTreeN)(self.read_nodes)
        self.app.post("/nodes")(self.save_nodes)
        self.app.post("/upgrade")(self.upgrade)
        self.app.post("/shutdown")(self.shutdown)
        self.app.post("/restart")(self.restart)

        parent_app.mount(prefix, self.app)

    def read_funcs(self) -> SchemaF:
        return export_manager(self.program.manager)

    def read_nodes(self) -> NodeTreeN:
        return export_nodetree(self.program.pipeline)

    def save_nodes(self, *, nodetree: NodeTreeN):
        import_nodetree(self.program, nodetree)
        # only save if successful import
        self.program.persist.nodetree = nodetree

    def upgrade(self, file: UploadFile = File(...)):
        upgrade_opsi(file, self.program.lifespan)

    def shutdown(self):
        self.program.lifespan.shutdown()

    def restart(self):
        self.program.lifespan.shutdown(restart=True)
