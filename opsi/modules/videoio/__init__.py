from dataclasses import dataclass
from typing import Tuple

import engine

from opsi.manager.manager_schema import Function
from opsi.util.cv import Mat, MatBW
from opsi.util.unduplicator import Unduplicator

from .cameraserver import CameraSource, CamHook
from .input import controls, create_capture, get_modes, parse_camstring

__package__ = "opsi.videoio"
__version__ = "0.123"

UndupeInstance = Unduplicator()
HookInstance = CamHook()


class CameraInput(Function):
    require_restart = True

    def on_start(self):
        camNum = parse_camstring(self.settings.mode)[0]
        if not UndupeInstance.add(camNum):
            raise ValueError(f"Camera {camNum} already in use")

        self.cap = create_capture(self.settings)
        self.cap.read()  # test for errors

    @dataclass
    class Settings:
        mode: get_modes()
        brightness: int = 50
        contrast: int = 50
        saturation: int = 50
        exposure: int = 50
        width: controls() = None
        height: controls() = None
        fps: controls(True) = None

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        frame = None
        if self.cap:
            ret, frame = self.cap.read()
            frame = Mat(frame)
        return self.Outputs(img=frame)

    def dispose(self):
        camNum = parse_camstring(self.settings.mode)[0]
        UndupeInstance.remove(camNum)


class CameraServer(Function):
    has_sideeffect = True

    @classmethod
    def validate_settings(cls, settings):
        settings.name = settings.name.strip()

        return settings

    def on_start(self):
        if self.settings.backend == "MjpegCameraServer":
            self.src = MjpegCameraServer()
        elif self.settings.backend == "H264CameraServer":
            self.src = H264CameraServer()

    @dataclass
    class Settings:
        backend: ("MjpegCameraServer", "H264CameraServer")
        name: str = "camera"

    @dataclass
    class Inputs:
        img: Mat

    def run(self, inputs):
        self.src.run(inputs)
        return self.Outputs()

    def dispose(self):
        self.src.dispose()

    # Returns a unique string for each CameraServer instance
    @property
    def id(self):
        return self.settings.name


class MjpegCameraServer:
    def __init__(self):
        self.src = CameraSource()
        HookInstance.register(self)

    def run(self, inputs):
        if isinstance(inputs.img, MatBW):
            self.src.img = inputs.img.mat
        else:
            self.src.img = inputs.img

    def dispose(self):
        self.src.shutdown()
        HookInstance.unregister(self)


class H264CameraServer:
    def __init__(self):
        self.engine: engine.GStreamerEngineWriter = None

    def run(self, inputs: "CameraServer.Inputs"):
        if self.engine is None:
            # we need to set up engine
            size: Tuple[int, int, int] = (*inputs.img.img.size, 30)
            self.engine = engine.GStreamerEngineWriter(
                video_size=size, repeat_frames=True
            )
            return
        else:
            if isinstance(inputs.img, MatBW):
                img = inputs.img.mat
            else:
                img = inputs.img
            self.engine.write_frame(img)

    def dispose(self):
        self.engine.end()
