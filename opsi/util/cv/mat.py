import cv2
from numpy import ndarray

from opsi.util.cache import cached_property

from .shape import Point

_ERODE_DILATE_CONSTS = {
    "kernel": None,
    "anchor": (-1, -1),
    "borderType": cv2.BORDER_CONSTANT,
    "borderValue": -1,
}


class Mat:
    def __init__(self, img: ndarray):
        self.img = img
        self.res = Point._make_rev(img.shape)

    @classmethod
    def from_matbw(cls, matbw: "MatBW") -> "Mat":
        return cls(cv2.cvtColor(matbw.img, cv2.COLOR_GRAY2BGR))

    @property
    def mat(self):
        return self

    @property
    def matBW(self):
        raise TypeError

    # Operations

    def blur(self, radius: int) -> "Mat":
        radius = round(radius)

        # Box Blur
        # img = cv2.blur(self.img, (2 * radius + 1,) * 2)

        # Gaussian Blur
        img = cv2.GaussianBlur(self.img, (6 * radius + 1,) * 2, round(radius))

        # Median Filter
        # img = cv2.medianBlur(self.img, 2 * radius + 1)

        # Bilateral Filter
        # img = cv2.bilateralFilter(self.img, -1, radius, radius)

        return Mat(img)

    def hsv_threshold(self, hue: "Range", sat: "Range", lum: "Range") -> "MatBW":
        """
        hue: Hue range (min, max) (0 - 179)
        sat: Saturation range (min, max) (0 - 255)
        lum: Value range (min, max) (0 - 255)
        """

        ranges = tuple(zip(hue, lum, sat))
        img = cv2.inRange(cv2.cvtColor(self.img, cv2.COLOR_BGR2HSV), *ranges)

        return MatBW(img)

    def encode_jpg(self, quality=None) -> bytes:
        params = ()

        if quality is not None:
            params = (int(cv2.IMWRITE_JPEG_QUALITY), int(quality))

        return cv2.imencode(".jpg", self.img, params)[1].tobytes()

    @cached_property
    def greyscale(self) -> "Mat":
        a = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        return Mat(a)

    def resize(self, res: Point) -> "Mat":
        return Mat(cv2.resize(img, res))


class MatBW:
    def __init__(self, img: ndarray):
        self.img = img
        self._mat = None
        self.res = Point._make_rev(img.shape)

    @property
    def mat(self):
        if self._mat is None:  # TODO: should this be cached? draw on mat in place?
            self._mat = Mat.from_matbw(self)
        return self._mat

    @property
    def matBW(self):
        return self

    # Operations

    def erode(self, size: int) -> "MatBW":
        return MatBW(cv2.erode(img, iterations=round(size), **ERODE_DILATE_CONSTS))

    def dilate(self, size: int) -> "MatBW":
        return MatBW(cv2.dilate(img, iterations=round(size), **ERODE_DILATE_CONSTS))

    @cached_property
    def invert(self) -> "MatBW":
        return MatBW(cv2.bitwise_not(self.img))

    @classmethod
    def join(cls, img1: "MatBW", img2: "MatBW") -> "MatBW":
        return MatBW(cv2.bitwise_or(img1, img2))
