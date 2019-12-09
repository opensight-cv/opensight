import logging

from dataclasses import Field, dataclass, fields, is_dataclass
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    List,
    NamedTuple,
    Type,
    get_type_hints,
)

from starlette.routing import Router

LOGGER = logging.getLogger(__name__)


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
    require_restart: bool = False
    disabled = False
    force_enabled = False

    SettingTypes: List[Field]
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

        cls.SettingTypes = fields(cls.Settings)
        cls.InputTypes = get_type_hints(cls.Inputs)
        cls.OutputTypes = get_type_hints(cls.Outputs)

        # Inject code that runs before the overridable methods
        # This patching is necessary to keep the api the same

        for func in ("run", "dispose", "validate_settings"):
            # Do not change these constants, unless you change the private functions defined below
            original = func
            renamed = "_" + func
            private = "_private_" + func

            # fix inheriting from Function
            # only override if it hasn't been already overwritten
            if getattr(cls, original) == getattr(cls, private):
                continue

            # copy original cls.func to cls._func
            setattr(cls, renamed, getattr(cls, original))
            # override original cls.func with our cls._private_func
            setattr(cls, original, getattr(cls, private))

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

    def dispose(self):
        pass

    def run(self, inputs) -> Outputs:
        return self.Outputs()

    def on_start(self):
        pass

    @classmethod
    def validate_settings(cls, settings):
        return settings

    # Private, do not override

    def __init__(self, settings: Settings):
        self.settings = settings
        self.alive = True

        try:
            self.on_start()
        except:
            self.dispose()
            raise

    def _private_dispose(self):
        try:
            self._dispose()
        finally:
            self.alive = False

    def _private_run(self, inputs) -> Outputs:
        if not self.alive:
            raise ValueError("Attempted to call function when already disposed")
        return self._run(inputs)

    @classmethod
    def _private_validate_settings(cls, settings):
        settings_new = cls._validate_settings(settings)

        # function must return settings
        if not isinstance(settings, cls.Settings):
            # raise error?
            settings_new = settings

        return settings_new


def isfunction(func):
    try:
        return issubclass(func, Function)
    except TypeError:  # func is not a type
        return False


class Hook:
    def __init__(self, visible=True):
        # self.app can be any ASGI app, but it must exist
        self.visible = visible
        self.app = Router()
        self.url = ""  # will be replaced during webserver init

    def cancel_dependents(self):
        try:
            self.pipeline.cancel_dependents(self.pipeline.current)
        except:
            raise ValueError("Pipeline not available! Cannot cancel dependents.")


def ishook(hook):
    return isinstance(hook, Hook)


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
