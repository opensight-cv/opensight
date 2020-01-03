import math

import cv2

from .types import *

OPENCV3 = False

if cv2.__version__[0] == "3":
    OPENCV3 = True


class Mat(ndarray):
    @property
    def mat(self):
        return self

    @property
    def matBW(self):
        raise TypeError


class MatBW(ndarray):
    def __array_finalize__(self, obj):
        self._mat = None

    @property
    def mat(self):
        if self._mat is None:
            self._mat = matBW_to_mat(self)
        return self._mat

    @property
    def matBW(self):
        return self


def blur(img: Mat, radius: int) -> Mat:
    """
    Args:
        img: Mat
        radius: blur strength (int)
    Returns:
        Mat (numpy.ndarray)
    """
    radius = round(radius)

    # Box Blur
    return cv2.blur(img.mat, (2 * radius + 1,) * 2).view(Mat)

    # Gaussian Blur
    # return cv2.GaussianBlur(img, (6 * radius + 1,) * 2, round(radius))

    # Median Filter
    # return cv2.medianBlur(img, 2 * radius + 1);

    # Bilateral Filter
    # return cv2.bilateralFilter(img, -1, radius, radius)


def hsv_threshold(img: Mat, hue: "Range", sat: "Range", lum: "Range") -> MatBW:
    """
    Args:
        img: Mat
        hue: Hue range (min, max) (0 - 359)
        sat: Saturation range (min, max) (0 - 255)
        lum: Value range (min, max) (0 - 255)
    Returns:
        Black+White Mat
    """
    hue = (hue[0] // 2, hue[1] // 2)
    ranges = tuple(zip(hue, lum, sat))
    return cv2.inRange(cv2.cvtColor(img.mat, cv2.COLOR_BGR2HSV), *ranges).view(MatBW)


def v_threshold(img: Mat, val: "Range") -> MatBW:
    """
       Args:
           img: Mat
           val: Value range (min, max) (0 - 255)
       Returns:
           Black+White Mat
       """
    return cv2.inRange(img.mat, val[0], val[1]).view(MatBW)


def hough_circles(
    img: Mat,
    dp: int,
    min_dist: int,
    param1: int,
    param2: int,
    min_radius: int,
    max_radius: int,
) -> "Circles":
    return cv2.HoughCircles(
        img,
        method=cv2.HOUGH_GRADIENT,
        dp=dp,
        minDist=min_dist,
        param1=param1,
        param2=param2,
        minRadius=min_radius,
        maxRadius=max_radius,
    )


def hough_lines(
    img: Mat,
    rho: int,
    threshold: int,
    min_length: int,
    max_gap: int,
    theta: float = math.pi / 180.0,
) -> "Segments":
    return cv2.HoughLinesP(
        img,
        rho=rho,
        theta=theta,
        threshold=threshold,
        minLineLength=min_length,
        maxLineGap=max_gap,
    )


def canny(img: Mat, threshold_lower, threshold_upper) -> MatBW:
    return cv2.Canny(img, threshold_lower, threshold_upper)


ERODE_DILATE_CONSTS = {
    "kernel": None,
    "anchor": (-1, -1),
    "borderType": cv2.BORDER_CONSTANT,
    "borderValue": -1,
}


def erode(img: MatBW, size: int) -> MatBW:
    """
    Args:
        img: Mat
        size: Number of iterations (int)
    Returns:
        Mat
    """
    return cv2.erode(img.matBW, iterations=round(size), **ERODE_DILATE_CONSTS).view(
        MatBW
    )


def dilate(img: MatBW, size: int) -> MatBW:
    """
    Args:
        img: Mat
        size: Number of iterations (int)
    Returns:
        Mat
    """
    return cv2.dilate(img.matBW, iterations=round(size), **ERODE_DILATE_CONSTS).view(
        MatBW
    )


FIND_CONTOURS_CONSTS = {"mode": cv2.RETR_LIST, "method": cv2.CHAIN_APPROX_SIMPLE}


def find_contours(img: MatBW) -> "Contours":
    """
    Args:
        img: Black+White Mat
    Returns:
        Contours (list of numpy.ndarray)
    """
    vals = cv2.findContours(img.matBW, **FIND_CONTOURS_CONSTS)

    if OPENCV3:
        return vals[1]  # image, contours, hierarchy
    else:
        return vals[0]  # contours, hierarchy


def convex_hulls(contours: "Contours") -> "Contours":
    """
    Args:
        contours: Contours (list of numpy.ndarray)
    Returns:
        Contours (list of numpy.ndarray)
    """
    return [cv2.convexHull(contour) for contour in contours]


def matBW_to_mat(img: MatBW) -> Mat:
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR).view(Mat)


def encode_jpg(img: Mat, quality=None) -> bytes:
    params = ()

    if quality is not None:
        params = (int(cv2.IMWRITE_JPEG_QUALITY), int(quality))

    return cv2.imencode(".jpg", img, params)[1].tobytes()


resize = cv2.resize


def invert(img: MatBW) -> MatBW:
    return cv2.bitwise_not(img.matBW)


def joinBW(img1: MatBW, img2: MatBW) -> MatBW:
    return cv2.bitwise_or(img1.matBW, img2.matBW)


def greyscale(img: Mat) -> Mat:
    return cv2.cvtColor(img.mat, cv2.COLOR_BGR2GRAY).view(Mat).mat


def bgr_to_hsv(img: Mat) -> Mat:
    return cv2.cvtColor(img.mat, cv2.COLOR_BGR2HSV)


def abs_diff(img, scalar):
    return cv2.absdiff(img, scalar)
