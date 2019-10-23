import cv2

from .types import *

OPENCV3 = False

if cv2.__version__[0] == "3":
    OPENCV3 = True


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
    return cv2.blur(img, (2 * radius + 1,) * 2)

    # Gaussian Blur
    # return cv2.GaussianBlur(img, (6 * radius + 1,) * 2, round(radius))

    # Median Filter
    # return cv2.medianBlur(img, 2 * radius + 1);

    # Bilateral Filter
    # return cv2.bilateralFilter(img, -1, radius, radius)


def hsv_threshold(img: Mat, hue: Range, sat: Range, lum: Range) -> MatBW:
    """
    Args:
        img: Mat
        hue: Hue range (min, max) (0 - 179)
        sat: Saturation range (min, max) (0 - 255)
        lum: Value range (min, max) (0 - 255)
    Returns:
        Black+White Mat
    """
    ranges = tuple(zip(hue, lum, sat))
    return cv2.inRange(cv2.cvtColor(img, cv2.COLOR_BGR2HSV), *ranges)


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
    return cv2.erode(img, iterations=round(size), **ERODE_DILATE_CONSTS)


def dilate(img: MatBW, size: int) -> MatBW:
    """
    Args:
        img: Mat
        size: Number of iterations (int)
    Returns:
        Mat
    """
    return cv2.dilate(img, iterations=round(size), **ERODE_DILATE_CONSTS)


FIND_CONTOURS_CONSTS = {"mode": cv2.RETR_LIST, "method": cv2.CHAIN_APPROX_SIMPLE}


def find_contours(img: MatBW) -> Contours:
    """
    Args:
        img: Black+White Mat
    Returns:
        Contours (list of numpy.ndarray)
    """
    vals = cv2.findContours(img, **FIND_CONTOURS_CONSTS)

    if OPENCV3:
        return vals[1]  # image, contours, hierarchy
    else:
        return vals[0]  # contours, hierarchy


def convex_hulls(contours: Contours) -> Contours:
    """
    Args:
        contours: Contours (list of numpy.ndarray)
    Returns:
        Contours (list of numpy.ndarray)
    """
    return [cv2.convexHull(contour) for contour in contours]


def matBW_to_mat(img: MatBW) -> Mat:
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
