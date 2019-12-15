from typing import List

import cv2
from numpy import ndarray

from opsi.util.cache import cached_property

from .mat import Mat, MatBW
from .shape import Point, Rect


class Contour:
    # https://docs.opencv.org/trunk/dd/d49/tutorial_py_contour_features.html
    # https://docs.opencv.org/3.4/d0/d49/tutorial_moments.html

    def __init__(self, raw: ndarray, res: Point):
        self.raw = raw  # Raw ndarray
        self.res = res

    @cached_property
    def convex_hull(self):
        raw_convex = cv2.convexHull(self.raw)
        contour = Contour(raw_convex, self.res)
        contour.convex_hull = contour

        return contour

    @cached_property
    def moments(self):
        return cv2.moments(self.raw)

    @cached_property
    def area(self):  # 0 - 1, percent of full area
        raw_area = self.moments["m00"]
        full_area = self.res.area
        area = raw_area / full_area

        return area

    @cached_property
    def _centroid(self):  # (x, y), unscaled
        M = self.moments
        area = M["m00"] + EPSILON

        cx = M["m10"] / area
        cy = M["m01"] / area

        return (cx, cy)

    @cached_property
    def centroid(self):  # (x, y), -1 to 1, where (0, 0) is the center
        cx, cy = self._centroid

        cx = ((cx * 2) / self.res.x) - 1
        cy = ((cy * 2) / self.res.y) - 1

        return Point(cx, cy)

    @cached_property
    def _arc_length(self):
        return cv2.arcLength(self.raw, True)

    @cached_property
    def perimeter(self):
        raw_perimeter = self._arc_length
        full_perimeter = self.res.perimeter
        perimeter = raw_perimeter / full_perimeter  # percent of full_perimeter

        return perimeter

    # 4. Contour Approximation from tutorial_py_contour_features.html
    def approximate(self, epsilon):  # epsilon is 0-1, percent of perimeter
        length = epsilon * self._arc_length
        contour = cv2.approxPolyDP(self.raw, length, True)

        return contour

    @cached_property
    def to_rect(self):
        return Rect.from_contour(self.raw)


class Contours:
    def __init__(self):
        raise TypeError("Contours class must be made using Contours.from_* classmethod")

    @classmethod
    def from_img(cls, img: MatBW):
        img = img.matBW
        res = Point._make_rev(img.shape)  # img.shape is (height, width),

        inst = cls.from_raw(_find_contours_raw(img), res)

        return inst

    @classmethod
    def from_raw(cls, raw: List[ndarray], res):
        inst = cls.__new__(cls)

        inst.raw = raw
        inst.res = res

        return inst

    @classmethod
    def from_contours(cls, contours: List[Contour], res=None):
        inst = cls.__new__(cls)

        inst.l = contours
        inst.res = res

        return inst

    # So the idea is that

    @cached_property
    def raw(self):  # used when contours is supplied but not raw
        return [contour.raw for contour in self.l]

    @cached_property
    def l(self):  # used when raw is supplied but not contour; must have self.res set
        return [Contour(contour, self.res) for contour in self.raw]

    @cached_property
    def convex_hulls(self):
        contours = [contour.convex_hull for contour in self.l]

        inst = self.__class__.from_contours(contours, self.res)
        inst.convex_hull = contours

        return inst

    def approximate(self, epsilon):
        contours = [contour.approximate(epsilon) for contour in self.l]

        inst = self.__class__.from_contours(contours, self.res)
        inst.approximate = contours

        return inst
