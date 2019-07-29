from dataclasses import dataclass, is_dataclass
from typing import Any, Callable, Dict, FrozenSet, NamedTuple, Type, get_type_hints


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
    disabled = False

    SettingTypes: Dict[str, Type]
    InputTypes: Dict[str, Type]
    OutputTypes: Dict[str, Type]

    type: str

    def __init_subclass__(cls, *args, **kargs):
        def error(msg):
            raise TypeError(f"Function {cls.__name__} must have a {msg}")

        if not does_match(cls, "Settings", is_dataclass):
            error("dataclass 'Settings'")

        if not does_match(cls, "Inputs", is_dataclass):
            error("dataclass 'Inputs'")

        if not does_match(cls, "Outputs", is_dataclass):
            error("dataclass 'Outputs'")

        if not does_match(cls, "has_sideeffect", is_bool):
            error("bool property 'has_sideeffect'")

        if not hasattr(cls, "require_restart"):
            error("property 'require_restart'")

        if not does_match(cls, "disabled", is_bool):
            error("bool property 'disabled'")

        cls.SettingTypes = get_type_hints(cls.Settings)
        cls.InputTypes = get_type_hints(cls.Inputs)
        cls.OutputTypes = get_type_hints(cls.Outputs)

        cls.require_restart = frozenset(cls.require_restart)
        for field in cls.require_restart:
            if field not in cls.InputTypes:
                error(f"field '{field}'")

        super().__init_subclass__(*args, **kargs)

    # Any of these dataclasses can be ommited to use the default

    @dataclass
    class Settings:
        pass

    @dataclass
    class Inputs:
        pass

    @dataclass
    class Outputs:
        pass

    # These are the main implementation methods that would
    # be defined in a concrete Function

    def __init__(self, settings: Settings):
        self.settings = settings

    def dispose(self):
        pass

    def run(self, inputs) -> Outputs:
        return self.Outputs()


def isfunction(func):
    try:
        return issubclass(func, Function)
    except TypeError:  # func is not a type
        return False


class ModulePath(NamedTuple):
    """
    ModulePath is used to locate a module to register
    path = path to module, relative or absolute. Can be empty for current directory
    name = name of file without .py extention
    """

    path: str
    name: str


class ModuleInfo(NamedTuple):
    """
    ModuleInfo is used to store metadata about the module
    after it has been registered
    """

    package: str
    version: str


class ModuleItem(NamedTuple):
    """
    ModuleItem is a single value in the 'modules' dict of a Manager
    """

    info: ModuleInfo
    funcs: Dict[str, Type[Function]]
