from typing import NamedTuple


class AnyType:
    pass


class _RangeBaseType:
    __slots__ = ("min", "max", "decimal")

    def __init__(self, min, max, *, decimal=True):
        self.decimal = bool(decimal)

        self.min = self._convert(min)
        self.max = self._convert(max)

    def _convert(self, val):
        return float(val) if self.decimal else int(round(val))

    def in_range(self, val):
        return self.min <= self._convert(val) <= self.max

    def ensure_in_range(self, val, name):
        if not self.in_range(val):
            raise ValueError(
                f"Parameter {name} is out of range ({self.min}, {self.max}) with value {val}"
            )

        return self._convert(val)

    def serialize(self):
        return {key: getattr(self, key) for key in self.__slots__}


class Slide(_RangeBaseType):
    def create(self, val):
        return self.ensure_in_range(val, "val")


class Range(NamedTuple):
    min: float
    max: float


class RangeType(_RangeBaseType):
    def create(self, min, max):
        min = self.ensure_in_range(min, "min")
        max = self.ensure_in_range(max, "max")

        return Range(min, max)
