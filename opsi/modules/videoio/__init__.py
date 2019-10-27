from dataclasses import dataclass

from opsi.manager.manager_schema import Function
from opsi.manager.types import Mat
from .cameraserver import CameraSource, CamHook
from .input import controls, create_capture, get_modes, parse_camstring
from opsi.util.unduplicator import Unduplicator

__package__ = "opsi.videoio"
__version__ = "0.123"

UndupeInstance = Unduplicator()
HookInstance = CamHook()


class CameraInput(Function):
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
            frame = frame.view(Mat)
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
        self.src = CameraSource()
        HookInstance.register(self)

    @dataclass
    class Settings:
        name: str = "camera"

    @dataclass
    class Inputs:
        img: Mat

    def run(self, inputs):
        self.src.img = inputs.img
        return self.Outputs()

    def dispose(self):
        self.src.shutdown()
        HookInstance.unregister(self)

    # Returns a unique string for each CameraServer instance
    @property
    def id(self):
        return self.settings.name
