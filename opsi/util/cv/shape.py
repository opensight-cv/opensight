from math import atan2, cos, sin, sqrt
from typing import NamedTuple

import cv2
import numpy as np
from numpy import ndarray

from opsi.util.cache import cached_property


# Also represents dimensions
class Point(NamedTuple):
    def nt_serialize(self):
        return {"x": self.x, "y": self.y}

    # implicit classmethod Point._make - create from existing iterable

    x: float
    y: float

    @classmethod
    def _make_rev(cls, iter):  # make reversed (y, x)
        return cls(iter[1], iter[0])

    @property
    def area(self):
        return self.x * self.y

    @property
    def hypot(self):
        return ((self.x ** 2) + (self.y ** 2)) ** 0.5

    @property
    def perimeter(self):
        return 2 * (self.x + self.y)

    # usage: normalized = Point(width, height).normalize(Point(x, y))
    def normalize(self, point: "Point") -> "Point":
        x = (2 * point.x / self.x) - 1
        y = (2 * point.y / self.y) - 1

        return Point(x, y)


class Shape:
    def __init__(self):
        raise TypeError("Must be made with from_* classmethods")

    @property
    def perimeter(self):
        return None

    @property
    def area(self):
        return None


class Rect(Shape):
    def nt_serialize(self):
        return {
            "x": self.tl.x,
            "y": self.tl.y,
            "width": self.dim.x,
            "height": self.dim.y,
        }

    # create from top-left coordinate and dimensions
    @classmethod
    def from_params(cls, x, y, width, height):
        inst = cls.__new__(cls)

        inst.tl = Point(x, y)
        inst.dim = Point(width, height)

        return inst  # Big oof will occur if you forget this

    @classmethod
    def from_contour(cls, contour_raw):
        return cls.from_params(*cv2.boundingRect(contour_raw))

    @cached_property
    def tr(self):
        return Point(self.tl.x + self.dim.x, self.tl.y)

    @cached_property
    def bl(self):
        return Point(self.tl.x, self.tl.y + self.dim.y)

    @cached_property
    def br(self):
        return Point(self.tl.x + self.dim.x, self.tl.y + self.dim.y)

    @cached_property
    def center(self):
        return Point(self.tl.x + self.dim.x / 2, self.tl.y + self.dim.y / 2)

    @cached_property
    def perimeter(self):
        return self.dim.perimeter

    @cached_property
    def area(self):
        return self.dim.area


class RotatedRect(Shape):
    def nt_serialize(self):
        return {
            "cx": self.center.x,
            "cy": self.center.y,
            "width": self.dim.x,
            "heigh": self.dim.y,
            "angle": self.angle,
        }

    # create from top-left coordinate and dimensions
    @classmethod
    def from_params(cls, center, size, angle):
        inst = cls.__new__(cls)

        inst.center = Point(center[0], center[1])
        inst.dim = Point(size[0], size[1])
        inst.angle = angle

        return inst

    @classmethod
    def from_contour(cls, contour_raw):
        return cls.from_params(*cv2.minAreaRect(contour_raw))

    @cached_property
    def box_points(self):
        return cv2.boxPoints((self.center, self.dim, self.angle))

    @cached_property
    def perimeter(self):
        return self.dim.perimeter

    @cached_property
    def area(self):
        return self.dim.area

    # Returns the angle of the rectangle from -90 to 90, where 0 is the rectangle vertical on its shortest side.
    @cached_property
    def vertical_angle(self):
        rect_angle = self.angle
        if self.dim[0] > self.dim[1]:
            rect_angle += 90
        return rect_angle


# Stores corners used for SolvePNP
class Corners(NamedTuple):
    def nt_serialize(self):
        return {
            "tlx": self.tl.x,
            "tly": self.tl.y,
            "trx": self.tr.x,
            "try": self.tr.y,
            "blx": self.bl.x,
            "bly": self.bl.y,
            "brx": self.br.x,
            "bry": self.br.y,
        }

    tl: Point
    tr: Point
    bl: Point
    br: Point

    def to_matrix(self):
        return np.array([self.tl, self.tr, self.bl, self.br], dtype=np.float)

    def calculate_pose(self, object_points, camera_matrix, distortion_coefficients):
        img_points_mat = self.to_matrix()

        ret, rvec, tvec = cv2.solvePnP(
            object_points,
            img_points_mat,
            camera_matrix,
            distortion_coefficients,
            flags=cv2.SOLVEPNP_AP3P,
        )

        return ret, rvec, tvec


class Pose3D(NamedTuple):
    def nt_serialize(self):
        return {"rvec": self.rvec.ravel(), "tvec": self.tvec.ravel()}

    rvec: ndarray
    tvec: ndarray

    def position_2d(self, tilt_angle: float):
        #  var x = tVec.get(0, 0)[0];
        #  var z = FastMath.sin(tilt_angle) * tVec.get(1, 0)[0] + tVec.get(2, 0)[0] *  FastMath.cos(tilt_angle);
        x = self.tvec[0, 0]
        z = sin(tilt_angle) * self.tvec[1, 0] + cos(tilt_angle) * self.tvec[2, 0]

        distance = sqrt(x * x + z * z)

        # From Team 5190: Green Hope Falcons
        # https://github.com/FRC5190/2019CompetitionSeason/blob/51f1940c5742a74bdcd25c4c9b6e9cfe187ec2fa/vision/jevoisvision/modules/ghrobotics/ReflectiveTape/ReflectiveTape.py#L94

        # Find the horizontal angle between camera center line and target
        camera_to_target_angle = -atan2(x, z)

        rot, _ = cv2.Rodrigues(self.rvec)
        rot_inv = rot.transpose()

        pzero_world = np.matmul(rot_inv, -self.tvec)

        target_angle = -atan2(pzero_world[0][0], pzero_world[2][0])

        trans_2d = Point(
            distance * cos(camera_to_target_angle),
            distance * sin(camera_to_target_angle),
        )

        return trans_2d, target_angle, camera_to_target_angle, distance

    def object_to_image_points(
        self, obj_points, camera_matrix, distortion_coefficients
    ):
        img_points, jacobian = cv2.projectPoints(
            obj_points, self.rvec, self.tvec, camera_matrix, distortion_coefficients
        )
        return img_points.astype(np.int)


class Circles(ndarray):
    def nt_serialize(self):
        return {
            "x": [float(circle[0]) for circle in self[0]],
            "y": [float(circle[1]) for circle in self[0]],
            "radius": [float(circle[2]) for circle in self[0]],
        }


class Segments(ndarray):
    def nt_serialize(self):
        return {
            "x1": [float(seg[0][0]) for seg in self],
            "y1": [float(seg[0][1]) for seg in self],
            "x2": [float(seg[0][2]) for seg in self],
            "y2": [float(seg[0][3]) for seg in self],
        }
