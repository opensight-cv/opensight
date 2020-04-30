import json
import logging
import shlex
import subprocess
from typing import Tuple

from opsi.manager.netdict import NT_AVAIL, NetworkDict
from opsi.util.networking import choose_port

LOGGER = logging.getLogger(__name__)

try:
    import engine

    ENGINE_AVAIL = True
except ImportError:
    LOGGER.error("upgraded-engineer not found, disabling H264 support")
    ENGINE_AVAIL = False


class EngineManager:
    """
    Manages coordinating a single Engine to be used by every output.
    """

    def __init__(self, hook):
        self._on = False
        self.hook = hook
        self.pipelines = {}
        self.engine: engine.Engine = None

        ports = [554, 1181]
        self.port = choose_port(ports)
        if not self.port:
            raise ValueError(f"Unable to bind to any of ports {ports}")

    def register(self, func: "H264CameraServer"):
        if func.name in self.pipelines:
            raise ValueError("Cannot have duplicate name")
        pipeline = func.pipeline
        self.pipelines[func.name] = pipeline
        if NT_AVAIL:
            url = self.hook.url.split("/")[2].split(":")[0]
            port = "" if self.port == 554 else ":{self.port}"
            NetworkDict(f"/GStreamer/{func.name}")["/streams"] = [
                f"rtsp://{url}{port}/{func.name}",
            ]

    def unregister(self, func: "H264CameraServer"):
        try:
            del self.pipelines[func.name]
            if NT_AVAIL:
                NetworkDict("/GStreamer").delete(func.name)
        except KeyError:
            pass

    def start(self):
        # turn pipelines into JSON
        pipes = json.dumps([v for k, v in self.pipelines.items()])
        launch = f"{engine.core.DEFAULT_EXEC_PATH} --port {self.port} --pipes-as-json '{pipes}'"
        self.engine = engine.Engine(shlex.split(launch))
        self.engine.start()
        self._on = True

    def restart_engine(self):
        if self.engine:
            self.engine.stop()
        if len(self.pipelines) > 0:
            self.start()

    def shutdown(self):
        if self.engine:
            self.engine.stop()


class H264CameraServer:
    def __init__(self, name: str, fps: int):
        self.name = name
        self.fps = fps
        self.size: Tuple[int, int, int] = (0, 0, 0)
        self.engine: engine.GStreamerEngineWriter = None
        self.registered: bool = False

    def run(self, inputs: "CameraServer.Inputs"):
        if self.engine is None:
            # we need to set up engine
            shape = inputs.img.img.shape
            self.size: Tuple[int, int, int] = (shape[1], shape[0], self.fps)
            self.engine = engine.GStreamerEngineWriter(
                socket_path=self.shmem_socket,
                video_size=self.size,
                repeat_frames=True,
                autostart=False,
            )
            return
        else:
            img = inputs.img.mat.img
            self.engine.write_frame(img)

    def dispose(self):
        if self.engine:
            self.engine.stop()

    def register(self, EngineInstance):
        if self.registered:
            return
        EngineInstance.register(self)
        self.registered = True

    def unregister(self, EngineInstance):
        if not self.registered:
            return
        EngineInstance.unregister(self)
        self.registered = False

    @property
    def shmem_socket(self):
        return f"/tmp/{self.name}"

    @property
    def encoder(self):
        command = shlex.split("gst-inspect-1.0 omxh264enc")
        out = subprocess.run(
            command,
            env={"PAGER": "cat"},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )  # ensure gst-inspect doesn't lock up with more/less

        return "OpenMAX" if not out.returncode else "Software"

    @property
    def pipeline(self):
        url = f"/{self.name}"
        return {
            "input": {"SharedMemory": self.shmem_socket},
            "encoder": self.encoder,
            "size": {
                "width": self.size[0],
                "height": self.size[1],
                "framerate": self.fps,
            },
            "url": url,
        }
