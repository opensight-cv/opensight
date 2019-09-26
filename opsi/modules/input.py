import glob
import re
import subprocess
from collections import OrderedDict
from dataclasses import dataclass

import cv2

from opsi.manager.manager_schema import Function
from opsi.manager.types import Mat

__package__ = "demo.input"
__version__ = "0.123"


def get_w(string):
    cam, w, h, fps = parse_camstring(string)
    return w + h


def get_codec(v4l2_out):
    # for each codec, add the codec name and how the description from v4l2-ctl, regex allowed
    # order by priority
    codec = None
    codecs = [("MJPG", "Motion-JPEG, compressed"), ("YUYV", "YUYV \d:\d:\d")]
    for i in codecs:
        # [digit] '<CODEC NAME>' (<CODEC DESCRIPTION>)
        # ex. [1]: 'MJPG' (Motion-JPEG, compressed)
        pattern = "\[\d+\]: '" + i[0] + "' \(" + i[1] + "\) (.+)(\[\d+\]?|$)"
        lines = re.search(pattern, v4l2_out)
        if lines is not None:
            return (cv2.VideoWriter_fourcc(*i[0]), lines.group(1))
    return None


def get_cam_info(cam):
    sp_out = subprocess.run(
        f"v4l2-ctl -d {str(cam)} --list-formats-ext".split(), capture_output=True
    )
    return str(sp_out.stdout).replace("\\n", " ").replace("\\t", "")


def get_modes():
    all_modes = set()
    cameras = {}
    cam_list = (cam.replace("/dev/video", "") for cam in glob.glob("/dev/video*"))

    for cam in sorted(cam_list, key=int):
        caminfo = get_cam_info(cam)

        codec = get_codec(caminfo)
        if codec is None:
            continue

        # group 1: resolution
        # group 2: everything up until next instance of Size
        cam_modes = {}
        for match in re.finditer("Size: \w+ (\d+x\d+) ", codec[1]):
            resolution = match.group(1)
            # get everything from the current resolution to the next resolution
            line = re.search(
                f"{match.group(0)}(.+?)Size|{match.group(0)}(.+)", codec[1]
            )
            line = line.group(1) or line.group(2)
            fpses = set()
            for interval in re.finditer("nterval: \w+ \d+\.\d+s \((.+?) fps\)", line):
                fpses.add(float(interval.group(1)))
            # convert to float to use %g formatting, removing extraneous decimals
            all_modes.add(
                "Cam {0}: {1} @ {2:g} fps".format(cam, resolution, float(max(fpses)))
            )

    # sort by the width, since camera is sorted by glob and fps is sorted above
    return tuple(sorted(all_modes, key=get_w, reverse=True))


def parse_camstring(camstring):
    # group 3: any digit+ OR any digit+, decimal, any digit+
    m = re.search("Cam (\d+): (\d+)x(\d+) @ (\d+|\d+.\d+) fps", camstring)
    cam = int(m.group(1))
    w = int(m.group(2))
    h = int(m.group(3))
    fps = float(m.group(4))
    return (cam, w, h, fps)


class CameraInput(Function):
    def on_start(self):
        self.mode = parse_camstring(self.settings.mode)
        codec = get_codec(get_cam_info(self.mode[0]))
        self.cap = cv2.VideoCapture(self.mode[0])
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.mode[1])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.mode[2])
        self.cap.set(cv2.CAP_PROP_FPS, self.mode[3])
        self.cap.set(cv2.CAP_PROP_FOURCC, codec[0])

    @dataclass
    class Settings:
        mode: get_modes()

    @dataclass
    class Outputs:
        img: Mat

    def run(self, inputs):
        ret, frame = self.cap.read()
        return self.Outputs(img=frame)
