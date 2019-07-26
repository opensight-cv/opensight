from .schema import *
from ..backend.manager_schema import Function


def get_type(type) -> InputOutputF:
    # todo: params
    return InputOutputF(type=type.__name__, params={})


def get_types(types):
    return {name: get_type(type) for name, type in types}


def _serialize_funcs(funcs: Dict[str, Type[Function]]) -> List[FunctionF]:
    func_schemas = []

    for func in funcs.values():
        function = FunctionF(
            name=func.__name__,
            type=func.type,
            settings=get_types(func.SettingTypes.items()),
            inputs=get_types(func.InputTypes.items()),
            outputs=get_types(func.OutputTypes.items()),
        )

        func_schemas.append(function)

    return func_schemas


def _serialize_modules(modules) -> List[ModuleF]:
    module_schemas = []

    for mod_package, mod in modules.items():
        module_schemas.append(
            ModuleF(
                package=mod_package,
                version=mod.info.version,
                funcs=_serialize_funcs(mod.funcs),
            )
        )

    return module_schemas


def export_manager(manager) -> SchemaF:
    return SchemaF(modules=_serialize_modules(manager.modules))
    # return SchemaF(funcs=_serialize_funcs(manager.funcs))


def export_nodetree(pipeline) -> NodeTreeN:
    pass  # todo


def inport_nodetree(pipeline, nodetree: NodeTreeN):
    pass  # todo
