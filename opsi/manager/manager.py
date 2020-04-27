import importlib
import inspect
import logging
import sys
from typing import Dict, List, Tuple, Type

from opsi.util.path import join

from .manager_schema import (
    Function,
    Hook,
    ModuleInfo,
    ModuleItem,
    ModulePath,
    isfunction,
    ishook,
)

LOGGER = logging.getLogger(__name__)


def import_module(path: ModulePath):
    """
    # So this sometimes doesn't work if the module name also exists in site-packages
    # But I don't understand exactly when and why this happens

    path_bak = sys.path[:]
    try:
        sys.path.insert(0, os.path.abspath(path.path))
        return importlib.import_module(path.name)
    except ImportError as e:
        # for error, print only error name (which is likely a missing dependency) and print full exception in debug
        LOGGER.error(
            'Encountered error when importing module %s due to "%s", skipping...',
            path.name,
            e,
        )
        LOGGER.debug("", exc_info=False)
    finally:
        sys.path = path_bak[:]
    """

    possible_names = (f"{path.name}.py", f"{path.name}/__init__.py")

    try:
        for filename in possible_names:
            module = _import_module(path, filename)
            if module:
                return module

        else:
            # Tried all possible paths, this module does not exist
            # importlib.import_module would raise ModuleNotFoundError
            # spec.loader.exec_module would raise FileNotFoundError

            LOGGER.error(
                "Module %s does not exist, skipping...", path.name,
            )
            return

    except ImportError as e:
        LOGGER.error(
            "Encountered error importing module '%s' due to %r, skipping...",
            path.name,
            e,
        )


def _import_module(path: ModulePath, filename: str):
    # To import a package, pass in the package's __init__.py
    # Returns None if file does not exist

    full_path = join(path.path, filename)

    # https://docs.python.org/3.7/library/importlib.html#importing-a-source-file-directly

    spec = importlib.util.spec_from_file_location(path.name, full_path)
    module = importlib.util.module_from_spec(spec)

    # This will break if the standard library package is imported, I think?
    # But it's necessary for inspect.getmodule to work
    sys.modules[path.name] = module

    try:
        spec.loader.exec_module(module)
    except FileNotFoundError:
        try:
            del sys.modules[path.name]
        except KeyError:
            pass

        return

    return module


class Manager:
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.modules: Dict[str, ModuleItem] = {}
        self.funcs: Dict[str, Type[Function]] = {}
        self.hooks: Dict[str, Hook] = {}

    @classmethod
    def is_valid_function(cls, module):
        def closure(func):
            # Todo: are there any other times we don't want to register a Function?
            # This is important because the default is registering every single Function
            return isfunction(func) and not func.disabled

        return closure

    @classmethod
    def get_module_info(cls, module):
        # Generate ModuleInfo from global variables in a module, with fallbacks

        package = getattr(module, "__package__", module.__name__)
        version = getattr(module, "__version__", "1.0")

        return ModuleInfo(package, version)

    def register_module(self, path: ModulePath):
        module = import_module(path)
        if not module:
            return
        info = Manager.get_module_info(module)

        hooks_tuple = inspect.getmembers(module, ishook)

        if len(hooks_tuple) == 1:
            hook = hooks_tuple[0][1]
            self.hooks[info.package] = hook
            hook.pipeline = self.pipeline
            hook.persist = self.pipeline.program.lifespan.persist
            hook.startup()
        elif len(hooks_tuple) > 1:
            LOGGER.error(f"Only one Hook per module allowed: {info.package}")
            return

        funcs_tuple: List[Tuple[str, Type[Function]]]
        funcs_tuple = inspect.getmembers(module, Manager.is_valid_function(module))

        # Since modules can have hooks now, the module should be registered even
        # if it does not have any Functions, because it could have a Hook.

        funcs: Dict[str, Type[Function]] = {}

        for name, func in funcs_tuple:
            func.type = info.package + "/" + name

            funcs[name] = func
            self.funcs[func.type] = func

        self.modules[info.package] = ModuleItem(info, funcs)

    def pipeline_update(self):
        for hook in self.hooks.values():
            hook.pipeline_update()

    def shutdown(self):
        for hook in self.hooks.values():
            hook.shutdown()
