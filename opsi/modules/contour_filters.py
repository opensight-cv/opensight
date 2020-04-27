from dataclasses import dataclass

from opsi.manager.manager_schema import Function
from opsi.manager.types import RangeType, Slide
from opsi.util.cv import Contour, Contours

__package__ = "opsi.contour-filter-ops"
__version__ = "0.123"


class ContourFilter(Function):
    disabled = True

    def check_contour(self, contour: Contour) -> bool:
        raise NotImplementedError()

    @dataclass
    class Inputs:
        contours: Contours

    @dataclass
    class Outputs:
        contours: Contours

    def run(self, inputs):
        contours = inputs.contours.l

        # Don't bother filtering if there are no contours in the input
        if len(contours) == 0:
            return self.Outputs(contours=Contours.from_contours([]))

        return self.Outputs(
            contours=Contours.from_contours(list(filter(self.check_contour, contours)))
        )


class AreaFilter(ContourFilter):
    disabled = False

    @dataclass
    class Settings:
        # TODO Make this into a slider once number input for sliders is implemented, because it really needs fine
        #  control
        min_area_pct: float = 0.0
        max_area_pct: float = 100.0

    def check_contour(self, contour: Contour) -> bool:
        area_pct = contour.area * 100.0
        return self.settings.min_area_pct < area_pct < self.settings.max_area_pct


class BoundingRectFilter(ContourFilter):
    disabled = False

    @dataclass
    class Settings:
        bounding_rectangle_pct: RangeType(min=0, max=100)

    def check_contour(self, contour: Contour) -> bool:
        screen_area = contour.res.area
        rect_area_pct = contour.to_rect.area / screen_area

        contour_area_pct = contour.area

        area_pct = (contour_area_pct / rect_area_pct) * 100.0

        return (
            self.settings.bounding_rectangle_pct.min
            < area_pct
            < self.settings.bounding_rectangle_pct.max
        )


class MinRectFilter(ContourFilter):
    disabled = False

    @dataclass
    class Settings:
        rectangle_pct: RangeType(min=0, max=100)

    def check_contour(self, contour: Contour) -> bool:
        screen_area = contour.res.area
        rect_area_pct = contour.to_min_area_rect.area / screen_area

        contour_area_pct = contour.area

        area_pct = (contour_area_pct / rect_area_pct) * 100.0
        return (
            self.settings.rectangle_pct.min < area_pct < self.settings.rectangle_pct.max
        )


class SpeckleFilter(Function):
    @dataclass
    class Inputs:
        contours: Contours

    @dataclass
    class Outputs:
        contours: Contours

    @dataclass
    class Settings:
        min_relative_area: Slide(min=0, max=100)

    def run(self, inputs):
        contours = inputs.contours.l
        if len(contours) == 0:
            return self.Outputs(contours=Contours.from_contours([]))

        # Find the area of the largest contour
        largest_area = max(contours, key=lambda contour: contour.area).area

        # Any contour below this area is considered a "speckle"
        speckle_threshold = largest_area * self.settings.min_relative_area / 100.0

        filtered = filter(lambda contour: contour.area > speckle_threshold, contours)

        return self.Outputs(contours=Contours.from_contours(list(filtered)))


class AspectRatioFilter(ContourFilter):
    disabled = False

    @dataclass
    class Settings:
        aspect_ratio_min: float = 1.0
        aspect_ratio_max: float = 10.0

    def check_contour(self, contour: Contour) -> bool:
        # Dimensions of the minimum area rectangle
        dim = contour.to_min_area_rect.dim

        # Make sure aspect ratio is > 1
        if dim[0] > dim[1]:
            aspect_ratio = dim[0] / dim[1]
        else:
            aspect_ratio = dim[1] / dim[0]

        return (
            self.settings.aspect_ratio_min
            < aspect_ratio
            < self.settings.aspect_ratio_max
        )


class OrientationFilter(ContourFilter):
    disabled = False

    @dataclass
    class Settings:
        orientation: ("Vertical", "Horizontal")

    def check_contour(self, contour: Contour) -> bool:
        # angle from vertical of the minimum area rectangle
        angle = contour.to_min_area_rect.vertical_angle

        if self.settings.orientation == "Vertical":
            return -45 <= angle <= 45
        elif self.settings.orientation == "Horizontal":
            return angle <= -45 or angle >= 45
        else:
            return False


class AngleFilter(ContourFilter):
    disabled = False

    @dataclass
    class Settings:
        angle: RangeType(min=-45, max=45)

    def check_contour(self, contour: Contour) -> bool:
        # angle from vertical of the minimum area rectangle
        angle = contour.to_min_area_rect.angle

        if angle < -45:
            angle += 90

        return self.settings.angle.min <= angle <= self.settings.angle.max


class Sort(Function):
    filters = {
        "Top": lambda cnt: -cnt.centroid.y,
        "Bottom": lambda cnt: cnt.centroid.y,
        "Left": lambda cnt: -cnt.centroid.x,
        "Right": lambda cnt: cnt.centroid.x,
        "Center": lambda cnt: -cnt.centroid.hypot,
        "Largest": lambda cnt: cnt.area,
        "Smallest": lambda cnt: -cnt.area,
    }

    @dataclass
    class Settings:
        by: ("Top", "Bottom", "Left", "Right", "Center", "Largest", "Smallest")
        keep: ("One", "All", "Number")
        keep_amount: int

    @dataclass
    class Inputs:
        contours: Contours

    @dataclass
    class Outputs:
        contours: Contours

    def run(self, inputs):
        contours = inputs.contours.l
        if len(contours) == 0:
            return self.Outputs(contours=Contours.from_contours([]))

        sort_fn = self.filters[self.settings.by]

        sorted_contours = sorted(contours, key=sort_fn, reverse=True)

        if self.settings.keep == "One":
            contours_out = [sorted_contours[0]]
        elif self.settings.keep == "All":
            contours_out = sorted_contours
        else:
            if self.settings.keep_amount > len(sorted_contours):
                contours_out = sorted_contours
            else:
                contours_out = sorted_contours[: self.settings.keep_amount]

        return self.Outputs(contours=Contours.from_contours(contours_out))
