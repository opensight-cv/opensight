from dataclasses import dataclass

import cv2

from opsi.manager.manager_schema import Function
from opsi.manager.types import Mat

__package__ = "demo.input"
__version__ = "0.123"


class CameraInput(Function):
    def on_start(self):
        self.cap = cv2.VideoCapture(self.settings.camera)

    @dataclass
    class Settings:
        camera: int

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        ret, frame = self.cap.read()
        return self.Outputs(img=frame)
