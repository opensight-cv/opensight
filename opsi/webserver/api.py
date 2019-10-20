import logging
import subprocess

from fastapi import FastAPI, File, UploadFile
from starlette.responses import JSONResponse

from opsi.backend.upgrade import upgrade_opsi
from opsi.util.concurrency import FifoLock

from .schema import Network, NodeTreeN, SchemaF
from .serialize import *

LOGGER = logging.getLogger(__name__)


class Api:
    def __init__(self, parent_app, program, prefix="/api"):
        self.program = program

        self.app = FastAPI(openapi_prefix=prefix)

        self.app.exception_handler(NodeTreeImportError)(self.importerror_handler)

        self.app.get("/funcs", response_model=SchemaF)(self.read_funcs)
        self.app.get("/nodes", response_model=NodeTreeN)(self.read_nodes)
        self.app.post("/nodes")(self.save_nodes)
        self.app.post("/upgrade")(self.upgrade)
        self.app.post("/shutdown")(self.shutdown)
        self.app.post("/restart")(self.restart)
        self.app.post("/shutdown-host")(self.shutdown_host)
        self.app.post("/restart-host")(self.restart_host)
        self.app.post("/profile")(self.profile)
        self.app.post("/network")(self.network)

        parent_app.mount(prefix, self.app)

    def importerror_handler(self, request, exc):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid Nodetree",
                "node": str(exc.node.id),
                "type": exc.node.type,
                "message": exc.args[0],
            },
        )

    def read_funcs(self) -> SchemaF:
        return export_manager(self.program.manager)

    def read_nodes(self) -> NodeTreeN:
        with FifoLock(self.program.queue):
            return export_nodetree(self.program.pipeline)

    def save_nodes(self, *, nodetree: NodeTreeN):
        import_nodetree(self.program, nodetree)
        # only save if successful import
        self.program.lifespan.persist.nodetree = nodetree

    def upgrade(self, file: UploadFile = File(...)):
        upgrade_opsi(file, self.program.lifespan)

    def shutdown(self):
        self.program.lifespan.shutdown()

    def restart(self):
        if self.program.lifespan.using_systemd:
            self.program.lifespan.shutdown(restart=False)
        self.program.lifespan.shutdown(restart=True)

    def shutdown_host(self):
        self.program.lifespan.shutdown(host=True)

    def restart_host(self):
        self.program.lifespan.shutdown(host=True, restart=True)

    def profile(self, profile: int):
        if profile >= 10:
            return
        self.program.lifespan.persist.profile = profile
        self.program.lifespan.persist.update_nodetree()
        import_nodetree(self.program, self.program.lifespan.persist.nodetree)
        return profile

    def network(self, *, network: Network):
        self.program.lifespan.persist.network = network
        self.program.lifespan.persist.update_nodetree()
        self.program.lifespan.shutdown(restart=True)
        return {"team": network.team, "static": network.static}
