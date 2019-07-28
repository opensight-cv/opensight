from starlette.applications import Starlette
from starlette.staticfiles import StaticFiles

from ..backend.program import Program
from .api import Api


class WebServer:
    def __init__(self, program: Program):
        self.program = program

        self.app = Starlette()
        self.app.debug = True

        self.api = Api(self.app, self.program)
        self.app.mount("/", StaticFiles(directory="../async-frontend/nodeUI"))
