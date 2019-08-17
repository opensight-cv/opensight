from starlette.applications import Starlette
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles

from ..backend.program import Program
from .api import Api
from .test import WebserverTest


class WebServer:
    def __init__(self, program: Program):
        self.program = program

        self.app = Starlette()
        self.app.debug = True

        self.testclient = WebserverTest(self.app)
        self.api = Api(self.app, self.program)

        self.app.mount("/", StaticFiles(directory="opsi/frontend/nodeUI"))
        self.app.route("/")(lambda request: RedirectResponse(url="/index.html"))

    # These test functions go through the entire http pipeline

    def get_funcs(self) -> str:
        return self.testclient.get("/api/funcs")

    def get_nodes(self) -> str:
        return self.testclient.get("/api/nodes")

    def set_nodes(self, data: str) -> str:
        return self.testclient.post("/api/nodes", data)
