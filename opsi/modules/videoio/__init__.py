from dataclasses import dataclass

from opsi.manager.manager_schema import Function
from opsi.util.cv import Mat, MatBW
from opsi.util.unduplicator import Unduplicator

from .h264 import EngineManager, H264CameraServer
from .input import controls, create_capture, get_modes, parse_camstring
from .mjpeg import CamHook, MjpegCameraServer

__package__ = "opsi.videoio"
__version__ = "0.123"

UndupeInstance = Unduplicator()
HookInstance = CamHook()
EngineInstance = EngineManager(HookInstance)
HookInstance.add_listener("pipeline_update", EngineInstance.restart_engine)


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
    always_restart = False
    require_restart = True

    @classmethod
    def validate_settings(cls, settings):
        settings.name = settings.name.strip()
        return settings

    def on_start(self):
        if self.settings.backend == "MJPEG":
            HookInstance.register(self)
            self.always_restart = False
            self.src = MjpegCameraServer()
        elif self.settings.backend == "H.264 (30 FPS)":
            self.always_restart = True
            self.src = H264CameraServer(self.settings.name, 30)
        elif self.settings.backend == "H.264 (60 FPS)":
            self.always_restart = True
            self.src = H264CameraServer(self.settings.name, 60)

    @dataclass
    class Settings:
        name: str = "camera"
        backend: ("MJPEG", "H.264 (30 FPS)", "H.264 (60 FPS)") = "MJPEG"

    @dataclass
    class Inputs:
        img: Mat

    def run(self, inputs):
        self.src.run(inputs)
        if "H.264" in self.settings.backend:
            self.src.register(EngineInstance)
        return self.Outputs()

    def dispose(self):
        if self.settings.backend == "MJPEG":
            HookInstance.unregister(self)
        elif "H.264" in self.settings.backend:
            self.src.unregister(EngineInstance)
        self.src.dispose()

    # Returns a unique string for each CameraServer instance
    @property
    def id(self):
        return self.settings.name
