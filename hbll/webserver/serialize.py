from .schema import *
from ..backend.manager_schema import Function
from ..backend.pipeline import StaticLink, Link, Pipeline
from ..backend.pipeline_recursive import RecursiveLink

from dataclasses import asdict


__all__ = ("export_manager", "export_nodetree", "import_nodetree")


# ---------------------------------------------------------


def get_type(type) -> InputOutputF:
    # todo: params
    return InputOutputF(type=type.__name__, params={})


def get_types(types):
    return {name: get_type(type) for name, type in types}


def _serialize_funcs(funcs: Dict[str, Type[Function]]) -> List[FunctionF]:
    return [
        FunctionF(
            name=func.__name__,
            type=func.type,
            settings=get_types(func.SettingTypes.items()),
            inputs=get_types(func.InputTypes.items()),
            outputs=get_types(func.OutputTypes.items()),
        )
        for func in funcs.values()
    ]


def _serialize_modules(modules) -> List[ModuleF]:
    return [
        ModuleF(
            package=mod_package,
            version=mod.info.version,
            funcs=_serialize_funcs(mod.funcs),
        )
        for mod_package, mod in modules.items()
    ]


def export_manager(manager) -> SchemaF:
    if FUNC_INSTEAD_OF_MODS:
        return SchemaF(funcs=_serialize_funcs(manager.funcs))
    else:
        return SchemaF(modules=_serialize_modules(manager.modules))


# ---------------------------------------------------------


def _serialize_settings(settings) -> Dict[str, Any]:
    if settings is None:
        return {}

    return asdict(settings)


def _serialize_link(link: Optional[Link]) -> Optional[LinkN]:
    if link is None:
        return None

    if isinstance(link, StaticLink):
        return None
    if isinstance(link, RecursiveLink):
        return LinkN(id=link.node.id, name=link.name)

    raise TypeError(f"Unknown link type: {type(link)}")


def _serialize_input(link: Optional[Link]) -> InputN:
    linkn = _serialize_link(link)

    if link is None:
        return InputN(link=linkn, value=None)

    if isinstance(link, StaticLink):
        return InputN(link=linkn, value=link.value)
    if isinstance(link, RecursiveLink):
        return InputN(link=linkn, value=None)

    raise TypeError(f"Unknown link type: {type(link)}")


def export_nodetree(pipeline: Pipeline) -> NodeTreeN:
    nodes: List[NodeN] = []

    for id, node in pipeline.nodes.items():
        nodes.append(
            NodeN(
                type=node.func_type.type,
                id=id,
                settings=_serialize_settings(node.settings),
                inputs={
                    name: (
                        _serialize_link(link)
                        if LINKS_INSTEAD_OF_INPUTS
                        else _serialize_input(link)
                    )
                    for name, link in node.inputLinks.items()
                },
            )
        )

    return NodeTreeN(nodes=nodes)


# ---------------------------------------------------------


def import_nodetree(pipeline, nodetree: NodeTreeN):
    pass  # todo
