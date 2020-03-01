from dataclasses import dataclass

import cv2
import numpy as np

from opsi.manager.manager_schema import Function, Hook
from opsi.util.cv import Mat

HookInstance = Hook()


class DrawFPS(Function):
    @dataclass
    class Inputs:
        img: Mat

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        fps_str = "{:.1f}".format(HookInstance.get_fps())
        draw = np.copy(inputs.img.mat.img)
        cv2.putText(
            draw,
            fps_str,
            (30, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            lineType=cv2.LINE_AA,
        )
        draw = Mat(draw)
        return self.Outputs(img=draw)
