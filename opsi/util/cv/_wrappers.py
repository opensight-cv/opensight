from typing import List, Tuple

import cv2
from numpy import ndarray

# from opsi.manager.types import Range

# Define dummy types, just for typehints
# Not the same classes as in the rest of util.cv
class Mat(ndarray):
    pass


class MatBW(ndarray):
    pass


def blur(img: Mat, radius: int) -> Mat:
    """
    Args:
        img: Mat
        radius: blur strength (int)
    Returns:
        Mat
    """
    radius = round(radius)

    # Box Blur
    return cv2.blur(img, (2 * radius + 1,) * 2)

    # Gaussian Blur
    # return cv2.GaussianBlur(img, (6 * radius + 1,) * 2, round(radius))

    # Median Filter
    # return cv2.medianBlur(img, 2 * radius + 1)

    # Bilateral Filter
    # return cv2.bilateralFilter(img, -1, radius, radius)


def hsv_threshold(img: Mat, hue: "Range", sat: "Range", lum: "Range") -> MatBW:
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


def _find_contours_raw(img: MatBW) -> List[ndarray]:
    """
    Internal use only
    Modules: use find_contours()
    Args:
        img: Black+White Mat
    Returns:
        List of numpy.ndarray
    """

    vals = cv2.findContours(img, **FIND_CONTOURS_CONSTS)

    #  return vals[1]  # OPENCV3: image, contours, hierarchy
    return vals[0]  # OPENCV4: contours, hierarchy


def matBW_to_mat(img: MatBW) -> Mat:
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


def encode_jpg(img: Mat, quality=None) -> bytes:
    params = ()

    if quality is not None:
        params = (int(cv2.IMWRITE_JPEG_QUALITY), int(quality))

    return cv2.imencode(".jpg", img, params)[1].tobytes()


def resize(img: Mat, res: Tuple[int, int]) -> Mat:  # (width, height)
    return cv2.resize(img, res)


def invert(img: MatBW) -> MatBW:
    return cv2.bitwise_not(img)


def joinBW(img1: MatBW, img2: MatBW) -> MatBW:
    return cv2.bitwise_or(img1, img2)


def greyscale(img: Mat) -> Mat:
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
