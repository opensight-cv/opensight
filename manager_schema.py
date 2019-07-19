import random
from collections import namedtuple
from dataclasses import dataclass, is_dataclass
from typing import Any, Callable, Dict, FrozenSet, Tuple, Type, get_type_hints


def isinstance_partial(type: Type) -> Callable[[Any], bool]:
    def partial(obj) -> bool:
        return isinstance(obj, type)

    return partial


is_bool = isinstance_partial(bool)


def does_match(cls, name: str, asserter: Callable[[Any], bool]) -> bool:
    item = getattr(cls, name, None)

    return (item is not None) and asserter(item)


class Function:
    has_sideeffect: bool = False
    require_restart: FrozenSet[str] = frozenset()
    disable = False

    InputTypes: Dict[str, Type]
    OutputTypes: Dict[str, Type]

    def __init_subclass__(cls, *args, **kargs):
        def error(msg):
            raise TypeError(f"Function {cls.__name__} must have a {msg}")

        if not does_match(cls, "Inputs", is_dataclass):
            error("dataclass 'Inputs'")

        if not does_match(cls, "Outputs", is_dataclass):
            error("dataclass 'Outputs'")

        if not does_match(cls, "has_sideeffect", is_bool):
            error("bool property 'has_sideeffect'")

        if not hasattr(cls, "require_restart"):
            error("property 'require_restart'")

        if not does_match(cls, "disable", is_bool):
            error("bool property 'disable'")

        cls.InputTypes = get_type_hints(cls.Inputs)
        cls.OutputTypes = get_type_hints(cls.Outputs)

        cls.require_restart = frozenset(cls.require_restart)
        for field in cls.require_restart:
            if field not in cls.InputTypes:
                error(f"field '{field}'")

        super().__init_subclass__(*args, **kargs)

    @dataclass
    class Settings:
        pass

    @dataclass
    class Inputs:
        pass

    @dataclass
    class Outputs:
        pass

    def __init__(self, settings: Settings):
        self.settings = settings

    def dispose(self):
        pass

    def run(self, inputs) -> Outputs:
        return self.Outputs()


# path.path = path to module, can be empty for curr dirr
# path.name = name of file w/o .py)
ModulePath = namedtuple("ModulePath", "path name")
ModuleInfo = namedtuple("ModuleInfo", "name version")
ModuleItem = namedtuple("ModuleItem", "info funcs")
