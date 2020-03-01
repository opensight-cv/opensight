import math
from dataclasses import dataclass

import cv2
import numpy as np

from opsi.manager.manager_schema import Function
from opsi.util.cv import Mat, Point
from opsi.util.cv.file_storage import read_calibration_file
from opsi.util.cv.shape import Corners, Pose3D
from opsi.util.persistence import Persistence

__package__ = "opsi.solvepnp"
__version__ = "0.123"


def get_calibration_files(persist: Persistence):
    calibration_paths = persist.get_all_calibration_files()
    return tuple([path.name for path in calibration_paths])


persist = Persistence()

# Coordinates of the points of the target in meters
target_points_outer = np.array(
    [
        [-0.498475, 0.0, 0.0],  # Top left
        [0.498475, 0.0, 0.0],  # Top right
        [-0.2492375, -0.4318, 0.0],  # Bottom left
        [0.2492375, -0.4318, 0.0],  # Bottom right
    ]
)

target_points_inner = np.array(
    [
        [-0.498475, 0.0, 0.74295],  # Top left
        [0.498475, 0.0, 0.74295],  # Top right
        [-0.2492375, -0.4318, 0.74295],  # Bottom left
        [0.2492375, -0.4318, 0.74295],  # Bottom right
    ]
)

axes_points = np.array(
    [[0, 0, 0], [0.5, 0, 0], [0, 0.5, 0], [0, 0, 0.5],]  # Origin  # +X  # +Y  # +Z
)


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

    def run(self, inputs):
        if inputs.corners is None:
            return self.Outputs(pose=None)

        if self.settings.reference_point == "Outer port":
            target_points = target_points_outer
        else:
            target_points = target_points_inner

        ret, rvec, tvec = inputs.corners.calculate_pose(
            target_points, self.camera_matrix, self.distortion_coefficients
        )

        if not ret or rvec is None or tvec is None:
            return self.Outputs(pose=None)

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

        (
            position,
            target_angle,
            camera_to_target_angle,
            distance,
        ) = inputs.pose.position_2d(cam_tilt_radians)

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


class VisualizeTargetPose(Function):
    @dataclass
    class Settings:
        calibration_file: get_calibration_files(persist=persist)
        draw_target: ("Outer port", "Inner port", "None (Axes only)")

    @dataclass
    class Inputs:
        pose: Pose3D
        img: Mat

    @dataclass
    class Outputs:
        img: Mat

    def on_start(self):
        calib_file_name = str(
            persist.get_calibration_file_path(self.settings.calibration_file)
        )

        self.camera_matrix, self.distortion_coefficients = read_calibration_file(
            calib_file_name
        )

    def run(self, inputs):
        if inputs.pose is None:
            return self.Outputs(img=inputs.img)

        draw = np.copy(inputs.img.mat.img)

        # Draw the inner or outer target
        if (
            self.settings.draw_target == "Outer port"
            or self.settings.draw_target == "Inner port"
        ):
            if self.settings.draw_target == "Outer port":
                target_img_points = inputs.pose.object_to_image_points(
                    target_points_outer.astype(np.float),
                    self.camera_matrix,
                    self.distortion_coefficients,
                )
            else:
                target_img_points = inputs.pose.object_to_image_points(
                    target_points_inner.astype(np.float),
                    self.camera_matrix,
                    self.distortion_coefficients,
                )

            cv2.line(
                draw,
                tuple(target_img_points[0].ravel()),
                tuple(target_img_points[1].ravel()),
                (0, 255, 255),
                2,
            )
            cv2.line(
                draw,
                tuple(target_img_points[1].ravel()),
                tuple(target_img_points[3].ravel()),
                (0, 255, 255),
                2,
            )
            cv2.line(
                draw,
                tuple(target_img_points[3].ravel()),
                tuple(target_img_points[2].ravel()),
                (0, 255, 255),
                2,
            )
            cv2.line(
                draw,
                tuple(target_img_points[2].ravel()),
                tuple(target_img_points[0].ravel()),
                (0, 255, 255),
                2,
            )
        # Draw axes
        axes_img_points = inputs.pose.object_to_image_points(
            axes_points.astype(np.float),
            self.camera_matrix,
            self.distortion_coefficients,
        )

        cv2.line(
            draw,
            tuple(axes_img_points[0].ravel()),
            tuple(axes_img_points[1].ravel()),
            (0, 0, 255),
            2,
        )
        cv2.line(
            draw,
            tuple(axes_img_points[0].ravel()),
            tuple(axes_img_points[2].ravel()),
            (0, 255, 0),
            2,
        )
        cv2.line(
            draw,
            tuple(axes_img_points[0].ravel()),
            tuple(axes_img_points[3].ravel()),
            (255, 0, 0),
            2,
        )

        draw = Mat(draw)
        return self.Outputs(img=draw)
