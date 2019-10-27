import logging

from fastapi import FastAPI, File, UploadFile
from starlette.responses import JSONResponse

import opsi
from opsi.backend.upgrade import upgrade_opsi
from opsi.util.concurrency import FifoLock

from .schema import Network, NodeTreeN, SchemaF
from .serialize import *

LOGGER = logging.getLogger(__name__)


class Api:
    def __init__(self, parent_app, program, prefix="/api"):
        self.program = program

        self.app = FastAPI(
            title="OpenSight API", version=opsi.__version__, openapi_prefix=prefix
        )

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
        json = {"error": "Invalid Nodetree", "message": exc.args[0]}

        if exc.node:
            json.update({"node": str(exc.node.id), "type": exc.node.type})

        return JSONResponse(status_code=400, content=json)

    def read_funcs(self) -> SchemaF:
        return export_manager(self.program.manager)

    def read_nodes(self) -> NodeTreeN:
        with FifoLock(self.program.queue):
            # Any successful modifications to program.pipeline are
            # guaranteed to be saved in persistence, so there is no need
            # to export the nodetree

            # return export_nodetree(self.program.pipeline)
            return self.program.lifespan.persist.nodetree

    def save_nodes(self, *, nodetree: NodeTreeN):
        import_nodetree(self.program, nodetree)
        # only save if successful import
        self.program.lifespan.persist.nodetree = nodetree
        return nodetree

    def upgrade(self, file: UploadFile = File(...)):
        upgrade_opsi(file, self.program.lifespan)

    def shutdown(self):
        self.program.lifespan.shutdown()

    def restart(self):
        self.program.lifespan.restart()

    def shutdown_host(self):
        self.program.lifespan.shutdown(host=True)

    def restart_host(self):
        self.program.lifespan.restart(host=True)

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
        self.program.lifespan.restart()
        return {"team": network.team, "static": network.static}
