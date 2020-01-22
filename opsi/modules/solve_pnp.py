import math
from dataclasses import dataclass

import numpy as np

from opsi.manager.manager_schema import Function
from opsi.util.cache import cached_property
from opsi.util.cv import Point
from opsi.util.cv.file_storage import read_calibration_file
from opsi.util.cv.shape import Corners, Pose3D
from opsi.util.persistence import Persistence

__package__ = "opsi.solvepnp"
__version__ = "0.123"



def get_calibration_files(persist: Persistence):
    calibration_paths = persist.get_all_calibration_files()
    return tuple([path.name for path in calibration_paths])


persist = Persistence()


class SolvePNP(Function):
    @dataclass
    class Settings:
        calibration_file: get_calibration_files(persist=persist)
        reference_point: ("Outer port", "Inner port")

    @dataclass
    class Inputs:
        corners: Corners

    @dataclass
    class Outputs:
        pose: Pose3D

    def on_start(self):
        calib_file_name = str(
            persist.get_calibration_file_path(self.settings.calibration_file)
        )

        self.camera_matrix, self.distortion_coefficients = read_calibration_file(
            calib_file_name
        )

    # Coordinates of the points of the target in meters
    target_points_outer = np.array(
        [
            [-0.498475, 0.0, 0.0],  # Top left
            [0.498475, 0.0, 0.0],  # Top right
            [-0.2492375, -0.2159, 0.0],  # Bottom left
            [0.2492375, -0.2159, 0.0],  # Bottom right
        ]
    )

    target_points_inner = np.array(
        [
            [-0.498475, 0.0, -0.74295],  # Top left
            [0.498475, 0.0, -0.74295],  # Top right
            [-0.2492375, -0.2159, -0.74295],  # Bottom left
            [0.2492375, -0.2159, -0.74295],  # Bottom right
        ]
    )

    # TODO Some way to actually calibrate the camera
    # camera_matrix = np.array(
    #     [
    #         [549.16440778, 0.0, 286.27258457],
    #         [0.0, 552.26641517, 188.54410636],
    #         [0.0, 0.0, 1.0],
    #     ]
    # )
    # distortion_coefficients = np.array(
    #     [[0.11201923, -0.43900659, 0.00620875, -0.00058852, 0.57582748]]
    # )

    def run(self, inputs):
        if inputs.corners is None:
            return self.Outputs(pose=None)

        if self.settings.reference_point == "Outer port":
            target_points = SolvePNP.target_points_outer
        else:
            target_points = SolvePNP.target_points_inner

        ret, rvec, tvec = inputs.corners.calculate_pose(
            target_points, self.camera_matrix, self.distortion_coefficients
        )

        return self.Outputs(pose=Pose3D(rvec=rvec, tvec=tvec))


class Position2D(Function):
    @dataclass
    class Settings:
        camera_tilt_degrees: float
        output_units: ("Degrees", "Radians")

    @dataclass
    class Inputs:
        pose: Pose3D

    @dataclass
    class Outputs:
        position: Point
        distance: float
        camera_angle: float
        target_angle: float
        success: bool

    def run(self, inputs):
        if inputs.pose is None:
            return self.Outputs(
                success=False,
                position=None,
                distance=None,
                camera_angle=None,
                target_angle=None,
            )

        cam_tilt_radians = math.radians(self.settings.camera_tilt_degrees)

        position, target_angle, camera_to_target_angle = inputs.pose.position_2d(
            cam_tilt_radians
        )

        distance = position.hypot

        if self.settings.output_units == "Degrees":
            camera_to_target_angle = math.degrees(camera_to_target_angle)
            target_angle = math.degrees(target_angle)

        return self.Outputs(
            success=True,
            position=position,
            distance=distance,
            camera_angle=camera_to_target_angle,
            target_angle=target_angle,
        )
