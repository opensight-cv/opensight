from dataclasses import asdict
from typing import Any, Callable, Dict, List, Optional, Type, TYPE_CHECKING

from ..backend.manager import Manager
from ..backend.manager_schema import Function, ModuleItem
from ..backend.pipeline import Connection, Link, Links, Pipeline, StaticLink
from ..backend.pipeline_recursive import RecursiveLink
from ..backend.program import Program
from ..backend.types import *
from .schema import *

__all__ = ("export_manager", "export_nodetree", "import_nodetree")


# ---------------------------------------------------------


def _parse_range(type):
    if not isinstance(type, RangeType):
        return None

    return InputOutputF(type="Range", params=type.serialize())


# If type is in _normal_types, then the type is supported and it has no params
_normal_types = {int, float, bool, str, Mat, MatBW, Contour, Contours}

# Each item in _abnormal_types takes in a type and returns InputOutputF if the
# parser supports the type, or None if it does not
_abnormal_types: List[Callable[[Type], Optional[InputOutputF]]]
_abnormal_types = [_parse_range]  # add new type parsers here


def get_type(type: Type) -> InputOutputF:
    if type in _normal_types:
        return InputOutputF(type=type.__name__, params={})

    for parser in _abnormal_types:
        IO = parser(type)

        if IO is not None:
            return IO

    raise TypeError(f"Unknown type {type}")


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


def _serialize_modules(modules: Dict[str, ModuleItem]) -> List[ModuleF]:
    return [
        ModuleF(
            package=mod_package,
            version=mod.info.version,
            funcs=_serialize_funcs(mod.funcs),
        )
        for mod_package, mod in modules.items()
    ]


def export_manager(manager: Manager) -> SchemaF:
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


def _process_node_links(program: Program, node: NodeN) -> List[str]:
    links: Links = {}
    empty_links: List[str] = []

    link: Optional[LinkN]

    for name, input in node.inputs.items():
        if LINKS_INSTEAD_OF_INPUTS:
            link = input
        else:
            link = input.link

        if link is None:
            empty_links.append(name)
            continue

        links[name] = Connection(link.id, link.name)

    program.pipeline.create_links(node.id, links)

    return empty_links


def _process_widget(type: Type, val):
    if isinstance(type, RangeType):
        # Val is a Tuple[float, float]
        # Convert to Range
        val = type.create(*val)

    return val


def _process_node_inputs(program: Program, node: NodeN):
    empty_links = _process_node_links(program, node)

    if LINKS_INSTEAD_OF_INPUTS:
        return

    # node.inputs : Dict[str, InputN]
    real_node = program.pipeline.nodes[node.id]

    for name in empty_links:
        type = real_node.func.InputTypes[name]
        real_node.set_staticlink(name, _process_widget(type, node.inputs[name].value))


def _process_node_settings(program: Program, node: NodeN):
    real_node = program.pipeline.nodes[node.id]

    settings = real_node.func_type.Settings(**node.settings)

    real_node.settings = settings


def import_nodetree(program: Program, nodetree: NodeTreeN):
    # return "NotImplemented"

    ids = [node.id for node in nodetree.nodes]
    program.pipeline.prune_nodetree(ids)

    for node in nodetree.nodes:
        if node.id not in program.pipeline.nodes:
            program.create_node(node.type, node.id)

    for node in nodetree.nodes:
        _process_node_settings(program, node)
        if LINKS_INSTEAD_OF_INPUTS:
            _process_node_links(program, node)
        else:
            _process_node_inputs(program, node)
