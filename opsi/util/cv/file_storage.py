import cv2

CAMERA_MATRIX_NAME = "camera_matrix"
DISTORTION_COEFFICIENTS_NAME = "distortion_coefficients"


def read_calibration_file(path: str):
    fs = cv2.FileStorage(path, cv2.FILE_STORAGE_READ)

    if fs.isOpened():
        cam_mat = fs.getNode(CAMERA_MATRIX_NAME).mat()
        dist_coeff = fs.getNode(DISTORTION_COEFFICIENTS_NAME).mat()
        return cam_mat, dist_coeff
    else:
        raise ValueError(
            "Specified calibration file does not exist or cannot be opened"
        )


def write_calibration_file(path: str, camera_matrix, distortion_coefficients):
    fs = cv2.FileStorage(path, cv2.FILE_STORAGE_WRITE)
    fs.write(CAMERA_MATRIX_NAME, camera_matrix)
    fs.write(DISTORTION_COEFFICIENTS_NAME, distortion_coefficients)
