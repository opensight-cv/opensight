from pathlib import Path

from jinja2 import Template
from starlette.routing import Route, Router

from opsi.manager.manager_schema import Hook
from opsi.util.networking import choose_port
from opsi.util.templating import LiteralTemplate

from .mjpeg import MjpegResponse

try:
    from opsi.manager.netdict import NetworkDict

    NT_AVAIL = True
except ImportError:
    NT_AVAIL = False


class CamHook(Hook):
    # Matches both "camera.mjpg" and "camera.mjpeg"
    ROUTE_URL = "/{func}.mjpe?g"  # Route to bind to
    STREAM_URL = "/{func}.mjpeg"  # Canonical path

    path = Path(__file__).parent
    with open(path / "mjpeg.html") as f:
        TEMPLATE = f.read()
    TEMPLATE = Template(TEMPLATE)

    CAMERA_NAME = "OpenSight: {func}"
    CAMERA_URL_NT = f"mjpeg:{{url}}{STREAM_URL}?"
    CAMERA_URL_WEB = f"{{url}}{STREAM_URL}"

    def __init__(self):
        super().__init__()

        self.app = Router()
        if NT_AVAIL:
            self.netdict = NetworkDict("/CameraPublisher")
        self.funcs = {}  # {name: route}
        self.cams = {}  # {name: url}
        self.index_route = [Route("/", LiteralTemplate(self.TEMPLATE, cams=self.cams))]
        self.listeners = {"startup": set(), "shutdown": set(), "pipeline_update": set()}

        self._update()

    def _update(self):
        self.app.routes = self.index_route + list(self.funcs.values())

    def endpoint(self, camserv):
        def response(request):
            return MjpegResponse(request, camserv)

        return response

    def register(self, func):
        if func.id in self.funcs:
            raise ValueError("Cannot have duplicate name")

        self.funcs[func.id] = Route(
            self.ROUTE_URL.format(func=func.id), self.endpoint(func)
        )
        self.cams[func.id] = self.CAMERA_URL_WEB.format(url=self.url, func=func.id)
        self._update()

        # https://github.com/wpilibsuite/allwpilib/blob/ec9738245d86ec5a535a7d9eb22eadc78dee88b4/wpilibj/src/main/java/edu/wpi/first/wpilibj/CameraServer.java#L313
        if NT_AVAIL:
            ntdict = self.netdict.get_subtable(self.CAMERA_NAME.format(func=func.id))
            ntdict["streams"] = [self.CAMERA_URL_NT.format(url=self.url, func=func.id)]

    def unregister(self, func):
        try:
            del self.funcs[func.id]
            del self.cams[func.id]
        except KeyError:
            pass

        if NT_AVAIL:
            self.netdict.delete_table(self.CAMERA_NAME.format(func=func.id))

        self._update()
