import importlib
import inspect
import sys
from typing import Dict, Tuple, List

from manager_schema import Function, ModulePath, ModuleInfo, ModuleItem


class Manager:
    def __init__(self):
        self.modules: Dict[str, Tuple[ModuleInfo, List[Function]]] = {}

    @classmethod
    def is_valid_function(cls, module):
        def closure(func):
            # Todo: are there any other times we don't want to register a Function?
            # This is important because the default is registering every single Function
            return (
                isinstance(func, Function)
                and (not func.disabled)
                # If a module imports a Function from another module, do not register that Function
                and (inspect.getmodule(func) == module)
            )

        return closure

    @classmethod
    def get_module_info(cls, module):
        # Generate ModuleInfo from global variables in a module, with fallbacks

        name = getattr(module, "__fullname__", module.__name__)
        version = getattr(module, "__version__", "1.0")

        return ModuleInfo(name, version)

    @classmethod
    def import_module(cls, path: ModulePath):
        path_bak = sys.path[:]
        try:
            sys.path.insert(0, path.path)
            return importlib.import_module(path.name)
        finally:
            sys.path = path_bak[:]

    def register_module(self, path: ModulePath):
        module = Manager.import_module(path)
        info = Manager.get_module_info(module)
        funcs = inspect.getmembers(module, Manager.is_valid_function(module))

        if len(funcs) == 0:
            # Todo: error, return value?
            print(f"No Functions found in module {path}")
            return

        self.modules[info.name] = ModuleItem(info, funcs)
