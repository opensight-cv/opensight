import enum as _enum
from functools import partial
from typing import get_type_hints


"""
Usage:
    @Enum
    class Name:
        value_1: ...
        value_2: ...
or
    @Enum(new_name)
    class Name:
        ...
"""


def Enum(cls, name=None):
    if isinstance(cls, str):  # being called as @Enum(new_name)
        return partial(Enum, name=cls)

    return _enum.Enum(
        name if name is not None else cls.__name__,
        names=[(x, x) for x in get_type_hints(cls).keys()],
        module=cls.__module__,
    )
