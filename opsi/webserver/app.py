import functools
import logging
import socket
from abc import abstractmethod

from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse, RedirectResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from opsi.util.path import join

from .api import Api
from .test import WebserverTest

LOGGER = logging.getLogger(__name__)


class WebServer:
    def __init__(self, program, frontend: str, port: int = None):
        self.program = program

        self.app = Starlette()
        self.app.debug = True

        self.port = self.__check_port__(port or 80)

        self.app.router.add_route("/", self.NodetreePage)
        self.app.router.add_route(
            "/settings",
            functools.partial(self.SettingsPage, persist=self.program.lifespan.persist),
        )

        self.testclient = WebserverTest(self.app)
        self.api = Api(self.app, self.program)

        self.app.mount("/", StaticFiles(directory=frontend))

    def __check_port__(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
            except socket.error as e:
                LOGGER.debug(f"Could not bind to port {port}.", exc_info=True)
                port = 8000
                LOGGER.debug(f"Binding to port {port} instead")
        return port

    # These test functions go through the entire http pipeline
    def get_funcs(self) -> str:
        return self.testclient.get("/api/funcs")

    def get_nodes(self) -> str:
        return self.testclient.get("/api/nodes")

    def set_nodes(self, data: str) -> str:
        return self.testclient.post("/api/nodes", data)

    class TemplatePage(HTTPEndpoint):
        def __init__(self, scope, recieve, send):
            # opsi/webserver/templates
            self.page = self.set_page()
            self.templates = Jinja2Templates(directory=join(__file__, "templates"))
            super().__init__(scope, recieve, send)

        @abstractmethod
        def set_page(self):
            pass

        async def get(self, request):
            return self.templates.TemplateResponse(self.page, {"request": request})

    class NodetreePage(TemplatePage):
        def set_page(self):
            return "nodetree.html"

    class SettingsPage(TemplatePage):
        def __init__(self, scope, recieve, send, persist=None):
            self.persist = persist
            super().__init__(scope, recieve, send)

        def set_page(self):
            return "settings.html"

        async def get(self, request):
            return self.templates.TemplateResponse(
                self.page, {"request": request, "profile": self.persist.profile}
            )
