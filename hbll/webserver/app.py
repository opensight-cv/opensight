from starlette.applications import Starlette
from starlette.responses import RedirectResponse
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

        self.app.route("/")(self.redirect_to_index)
        
    def redirect_to_index(self, request):
        return RedirectResponse(url="/index.html")
