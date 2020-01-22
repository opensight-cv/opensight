from typing import List, Tuple, Union

import cv2
from numpy import ndarray

from opsi.util.cache import cached_property

from .mat import Mat, MatBW
from .shape import Corners, Point, Rect, RotatedRect


class Contour:
    # https://docs.opencv.org/trunk/dd/d49/tutorial_py_contour_features.html
    # https://docs.opencv.org/3.4/d0/d49/tutorial_moments.html

    def __init__(self, raw: ndarray, res: Point):
        self.raw = raw  # Raw ndarray
        self.res = res

    # Operations

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
    def pixel_centroid(self):  # (x, y), unscaled
        M = self.moments
        area = M["m00"] + 1e-5

        cx = M["m10"] / area
        cy = M["m01"] / area

        return Point(cx, cy)

    @cached_property
    def centroid(self):  # (x, y), -1 to 1, where (0, 0) is the center
        cx, cy = self.pixel_centroid

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
        raw_contour = cv2.approxPolyDP(self.raw, length, True)

        return Contour(raw_contour, self.res)

    @cached_property
    def to_rect(self) -> Rect:
        return Rect.from_contour(self.raw)

    @cached_property
    def to_min_area_rect(self) -> RotatedRect:
        return RotatedRect.from_contour(self.raw)

    @cached_property
    def points(self) -> List[Point]:
        return [Point(*raw_point[0]) for raw_point in self.raw]

    @cached_property
    def corners(self) -> Tuple[bool, Union[Corners, None]]:
        centroid = self.pixel_centroid
        points = self.points
        if len(points) < 4:
            return False, None

        tl = next(
            (
                point
                for point in points
                if point.x < centroid.x and point.y < centroid.y
            ),
            None,
        )
        tr = next(
            (
                point
                for point in points
                if point.x > centroid.x and point.y < centroid.y
            ),
            None,
        )
        bl = next(
            (
                point
                for point in points
                if point.x < centroid.x and point.y > centroid.y
            ),
            None,
        )
        br = next(
            (
                point
                for point in points
                if point.x > centroid.x and point.y > centroid.y
            ),
            None,
        )

        if tl is None or tr is None or bl is None or br is None:
            return False, None
        else:
            return True, Corners(tl, tr, bl, br)


FIND_CONTOURS_CONSTS = {"mode": cv2.RETR_EXTERNAL, "method": cv2.CHAIN_APPROX_SIMPLE}


class Contours:
    raw: List[ndarray]
    res: Point

    def __init__(self):
        raise TypeError("Contours class must be made using Contours.from_* classmethod")

    @classmethod
    def from_img(cls, img: MatBW):
        vals = cv2.findContours(img.matBW.img, **FIND_CONTOURS_CONSTS)

        #  raw = vals[1]  # OPENCV3: image, contours, hierarchy
        raw = vals[0]  # OPENCV4: contours, hierarchy

        inst = cls.from_raw(raw, img.res)

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

    @cached_property
    def raw(self):  # used when contours is supplied but not raw
        return [contour.raw for contour in self.l]

    @cached_property
    def l(self):  # used when raw is supplied but not contour; must have self.res set
        return [Contour(contour, self.res) for contour in self.raw]

    # Operations

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

    @cached_property
    def centroids(self):
        return [contour.pixel_centroid for contour in self.l]

    @cached_property
    def centroid_of_all(self):
        cx = sum(centroid[0] for centroid in self.centroids) / len(self.centroids)
        cy = sum(centroid[1] for centroid in self.centroids) / len(self.centroids)

        return Point(cx, cy)
