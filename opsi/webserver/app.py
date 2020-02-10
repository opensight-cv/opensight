import logging
from os.path import join

from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse, RedirectResponse
from starlette.staticfiles import StaticFiles

import opsi
from opsi.util.networking import get_server_url
from opsi.util.templating import TemplateFolder

from .api import Api
from .test import WebserverTest

LOGGER = logging.getLogger(__name__)


class WebServer:
    def __init__(self, program, frontend: str, port: int = 80, prefix="/"):
        self.program = program

        self.app = Starlette(debug=True)

        self.url = get_server_url(program.lifespan, port, prefix)
        self.template = TemplateFolder(join(frontend, "templates"))

        self.app.add_route("/", self.template("nodetree.html"))
        self.app.add_route(
            "/settings",
            self.template(
                "settings.html",
                persist=self.program.lifespan.persist,
                daemon=self.program.lifespan.using_systemd,
                nt=self.program.lifespan.NT_AVAIL,
                netconf=self.program.lifespan.netconf_writable,
                version=opsi.__version__,
            ),
        )

        self.testclient = WebserverTest(self.app)
        self.api = Api(self.app, self.program)
        self.make_hooks()

        self.app.mount(
            "/", CacheControlMiddleware(StaticFiles(directory=join(frontend, "www")))
        )

    def make_hooks(self):
        PREFIX = "/hooks"
        HOOKS = {
            x[0]: x[1] for x in self.program.manager.hooks.items() if x[1].app
        }  # {package: app}

        self.app.add_route(
            PREFIX, self.template("hooks.html", prefix=PREFIX, packages=HOOKS.keys())
        )

        # This is required because "/hooks/package/{path}"" and "/hooks/package/"" trigger the mounted app,
        # but "/hooks/package" doesn't
        self.app.add_route(PREFIX + "/{path}", self.trailingslash_redirect)

        for package, hook in HOOKS.items():
            path = PREFIX + "/" + package

            hook.url = self.url + path.lstrip("/")
            self.app.mount(path, hook.app)

    def trailingslash_redirect(self, request):
        return RedirectResponse(request.url.path + "/")

    # These test functions go through the entire http pipeline
    def get_funcs(self) -> str:
        return self.testclient.get("/api/funcs")

    def get_nodes(self) -> str:
        return self.testclient.get("/api/nodes")

    def set_nodes(self, data: str) -> str:
        return self.testclient.post("/api/nodes", data)


class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-cache public max-age=0 must-validate"
        return response
