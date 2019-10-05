import logging
import socket

from starlette.applications import Starlette
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles

from .api import Api
from .test import WebserverTest

LOGGER = logging.getLogger(__name__)


class WebServer:
    def __init__(self, program, frontend: str, port: int = None):
        self.program = program

        self.app = Starlette()
        self.app.debug = True

        self.port = self.__check_port__(port or 80)

        self.testclient = WebserverTest(self.app)
        self.api = Api(self.app, self.program)

        self.app.mount("/", StaticFiles(directory=frontend, html=True))

    def __check_port__(self, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("0.0.0.0", port))
        except socket.error as e:
            LOGGER.debug("Could not bind to port 80.")
            port = 8000
        return port

    # These test functions go through the entire http pipeline
    def get_funcs(self) -> str:
        return self.testclient.get("/api/funcs")

    def get_nodes(self) -> str:
        return self.testclient.get("/api/nodes")

    def set_nodes(self, data: str) -> str:
        return self.testclient.post("/api/nodes", data)
