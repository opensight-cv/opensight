from typing import NamedTuple


class Color(NamedTuple):
    red: int
    green: int
    blue: int

    # Convert from 6-char hex
    @classmethod
    def create(cls, _rgb):
        try:
            rgb = _rgb.strip()

            if not rgb[0] == "#":
                raise ValueError("Must start with '#'")

            rgb = rgb[1:]
            if not len(rgb) == 6:
                raise ValueError("Must have 6 chars")

            rgb = rgb[0:2], rgb[2:4], rgb[4:6]
            rgb = [int(v, 16) for v in rgb]

            return cls(*rgb)

        except (ValueError, IndexError):
            raise ValueError(f"Cannot convert string '{_rgb}' to color")

    def nt_serialize(self):
        return {"red": self.red, "green": self.green, "blue": self.blue}


# Also represents dimensions
class Point(NamedTuple):
    def nt_serialize(self):
        return {"x": self.x, "y": self.y}

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
