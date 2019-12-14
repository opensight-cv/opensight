import importlib
import inspect
import logging
import os.path
import sys
from typing import Dict, List, Tuple, Type

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
        LOGGER.debug("", exc_info=True)
    finally:
        sys.path = path_bak[:]
    """

    # Workaround for now: only allow import .py file, not full package

    full_path = os.path.abspath(os.path.join(path.path, path.name + ".py"))

    # https://docs.python.org/3.7/library/importlib.html#importing-a-source-file-directly

    spec = importlib.util.spec_from_file_location(path.name, full_path)
    module = importlib.util.module_from_spec(spec)

    # This will break if the standard library package is imported, I think?
    # But it's necessary for inspect.getmodule to work
    sys.modules[path.name] = module

    spec.loader.exec_module(module)

    return module
    """


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
            return (
                isfunction(func)
                and (not func.disabled)
                # If a module imports a Function from another module, do not register that Function
                and (inspect.getmodule(func) == module or func.force_enabled)
            )

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
            setattr(hook, "pipeline", self.pipeline)
            setattr(hook, "persist", self.pipeline.program.lifespan.persist)
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

    def shutdown(self):
        for hook in self.hooks.values():
            hook.shutdown()
