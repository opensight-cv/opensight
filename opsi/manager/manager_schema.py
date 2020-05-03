import logging
from dataclasses import Field, dataclass, fields, is_dataclass
from typing import Any, Callable, Dict, List, NamedTuple, Type, get_type_hints

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
    always_restart: bool = False
    disabled = False

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

        if not hasattr(cls, "always_restart"):
            error("property 'always_restart'")

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
        if settings is None:
            raise ValueError("settings cannot be None")

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
        if func is Function:
            return False
        return issubclass(func, Function)
    except TypeError:  # func is not a type
        return False


class Hook:
    def __init__(self):
        self.app = None  # self.app can be any ASGI app, or None if not visible
        self.url = ""  # will be replaced during webserver init
        self.cache = {"skip": {}, "deps": {}}
        self.listeners = {"startup": set(), "shutdown": set(), "pipeline_update": set()}
        self.lastPipeline = None
        self.pipeline = None  # will be replaced during module init
        self.persist = None  # will be replaced during module init

    def update_cache(self):
        if not self.lastPipeline == self.pipeline.nodes:
            self.cache = {"skip": {}, "deps": {}}
        self.lastPipeline = self.pipeline.nodes

    def get_skips(self, node):
        self.update_cache()
        skip = self.cache["skip"].get(node)
        if skip is None:
            skip = self.pipeline.get_dependents(node)
            self.cache["skip"][node] = skip
        return skip

    def get_output_deps(self, node, output):
        self.update_cache()

        if node not in self.cache["deps"]:
            self.cache["deps"][node] = {}

        deps = self.cache["deps"][node].get(output)

        if deps is None:
            deps = []
            for i in self.pipeline.nodes.values():
                for link in i.inputLinks.values():
                    if link.node is node and link.name == output:
                        deps.append(i)
            self.cache["deps"][node][output] = deps

        return deps

    def cancel_node(self, node):
        try:
            # reset path cache if pipeline has changed
            skip = self.get_skips(node)
            self.pipeline.cancel_nodes(skip)
        except:
            raise ValueError("Pipeline not available! Cannot cancel dependents.")

    def cancel_current(self):
        self.cancel_node(self.pipeline.current)

    def cancel_output(self, output: str):
        node = self.pipeline.current
        deps = self.get_output_deps(node, output)
        for dep in deps:
            self.cancel_node(dep)

    def add_listener(self, event: str, function: callable):
        self.listeners[event].add(function)

    def remove_listener(self, event: str, function: callable):
        self.listeners[event].discard(function)

    def startup(self):
        for func in self.listeners["startup"]:
            func()

    def shutdown(self):
        for func in self.listeners["shutdown"]:
            func()

    def pipeline_update(self):
        for func in self.listeners["pipeline_update"]:
            func()

    def get_fps(self):
        return self.pipeline.fps.fps


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
