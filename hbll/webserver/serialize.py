from .schema import *


def get_type(type) -> InputOutputF:
    # todo: params
    return InputOutputF(type=type.__name__, params={})


def get_types(types):
    return {name: get_type(type) for name, type in types}


def export_manager(manager) -> SchemaF:
    schema = SchemaF()

    for mod_package, mod in manager.modules.items():
        module = ModuleF(package=mod_package, version=mod.info.version)

        for name, func in mod.funcs:
            function = FunctionF(
                name=name,
                type=func.type,
                settings=get_types(func.SettingTypes.items()),
                inputs=get_types(func.InputTypes.items()),
                outputs=get_types(func.OutputTypes.items()),
            )

            module.funcs.append(function)

        schema.modules.append(module)

    return schema


def export_nodetree(pipeline) -> NodeTreeN:
    pass  # todo


def inport_nodetree(pipeline, nodetree: NodeTreeN):
    pass  # todo
