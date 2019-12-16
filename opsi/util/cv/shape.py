from typing import NamedTuple

import cv2

from opsi.util.cache import cached_property


# Also represents dimensions
class Point(NamedTuple):
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
    # create from top-left coordinate and dimensions
    @classmethod
    def from_params(cls, x, y, width, height):
        inst = cls.__new__(cls)

        inst.tl = Point(x, y)
        inst.dim = Point(width, height)

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
