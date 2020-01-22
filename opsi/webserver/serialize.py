import logging
import sys
from collections import deque
from dataclasses import _MISSING_TYPE, asdict
from typing import Callable, Type

from opsi.manager.link import NodeLink
from opsi.manager.manager import Manager
from opsi.manager.manager_schema import Function, ModuleItem
from opsi.manager.pipeline import Connection, Link, Links, Pipeline, StaticLink
from opsi.manager.types import *
from opsi.util.concurrency import FifoLock

from ..util.cv import Contour, Contours, Mat, MatBW, Point
from ..util.cv.mat import Color
from ..util.cv.shape import Circles, Corners, Lines, Pose3D, Segments
from .schema import *

__all__ = (
    "export_manager",
    "export_nodetree",
    "import_nodetree",
    "NodeTreeImportError",
)


LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------


def _rangetype_serialize(type):
    if not isinstance(type, RangeType):
        return None

    return InputOutputF(type="range", params=type.serialize())


def _slide_serialize(type):
    if not isinstance(type, Slide):
        return None

    return InputOutputF(type="slide", params=type.serialize())


def _tuple_serialize(type):
    if not isinstance(type, tuple):
        return None

    return InputOutputF(type="tup", params={"options": type})


_type_name: Dict[Type, str] = {
    float: "dec",
    bool: "bol",
    MatBW: "mbw",
    Circles: "cls",
    Color: "col",
    Segments: "seg",
    Lines: "lin",
    Contour: "cnt",
    Contours: "cts",
    Point: "pnt",
    Corners: "crn",
    Pose3D: "p3d",
    AnyType: "any",
}
_normal_types = {int, str, Mat}

# Each item in _abnormal_types takes in a type and returns InputOutputF if the
# parser supports the type, or None if it does not
_abnormal_types: List[Callable[[Type[any]], Optional[InputOutputF]]] = [
    _slide_serialize,
    _rangetype_serialize,
    _tuple_serialize,
]  # add new type parsers here


def get_type(_type: Type) -> InputOutputF:
    if (_type is None) or (_type == type(None)):
        return None

    if _type in _type_name:
        name = _type_name.get(_type)
        return InputOutputF(type=name)
    elif _type in _normal_types:
        return InputOutputF(type=_type.__name__)

    for parser in _abnormal_types:
        IO = parser(_type)

        if IO is not None:
            return IO

    raise TypeError(f"Unknown type {_type} ({type(_type)})")


def get_field_type(field) -> InputOutputF:
    io = get_type(field.type)
    if field.default and type(field.default) is not _MISSING_TYPE:
        io.params["default"] = field.default
    return io


def get_types(types):
    pruned_types = []
    # if none, just don't show it
    for _type in types:
        if _type[1] is not type(None):
            pruned_types.append(_type)
    return {name: get_type(type) for name, type in pruned_types}


def get_settings_types(types):
    pruned_types = []
    # if none, just don't show it
    for _type in types:
        if type(_type.type) is not type(None):
            pruned_types.append(_type)
    return {field.name: get_field_type(field) for field in pruned_types}


def _serialize_funcs(funcs: Dict[str, Type[Function]]) -> List[FunctionF]:
    return [
        FunctionF(
            name=func.__name__,
            type=func.type,
            settings=get_settings_types(func.SettingTypes),
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


# removes all Nones from dict
def _prune_factory(inp):
    pruned = {}
    for i in inp:
        if i[1] is not None:
            pruned[i[0]] = i[1]
    return pruned


def _serialize_settings(settings) -> Dict[str, Any]:
    if settings is None:
        return {}

    return asdict(settings, dict_factory=_prune_factory)


def _serialize_link(link: Optional[Link]) -> Optional[LinkN]:
    if link is None:
        return None

    if isinstance(link, StaticLink):
        return None
    if isinstance(link, NodeLink):
        return LinkN(id=link.node.id, name=link.name)

    raise TypeError(f"Unknown link type: {type(link)}")


def _serialize_input(link: Optional[Link]) -> InputN:
    linkn = _serialize_link(link)

    if link is None:
        return InputN(link=linkn, value=None)

    if isinstance(link, StaticLink):
        return InputN(link=linkn, value=link.value)

    raise TypeError(f"Unknown link type: {type(link)}")


def export_nodetree(pipeline: Pipeline) -> NodeTreeN:
    nodes: List[NodeN] = []

    for id, node in pipeline.nodes.items():
        # allow importing legacy nodetrees
        try:
            node.pos = [] if node.pos is None else node.pos
        except AttributeError:
            node.pos = []
            LOGGER.debug("Initalized default node position, %s", node.id)
        nodes.append(
            NodeN(
                type=node.func_type.type,
                id=id,
                settings=_serialize_settings(node.settings),
                pos=node.pos,
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


class NodeTreeImportError(ValueError):
    def __init__(
        self, program, node: NodeN = None, msg="", *, exc_info=True, real_node=False
    ):
        program.pipeline.clear()
        program.pipeline.broken = True

        self.node = node

        # https://github.com/python/cpython/blob/10ecbadb799ddf3393d1fc80119a3db14724d381/Lib/logging/__init__.py#L1572
        if exc_info:
            if isinstance(exc_info, BaseException):
                exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
            elif not isinstance(exc_info, tuple):
                exc_info = sys.exc_info()

            msg += ": " + str(exc_info[1])

        if real_node:
            self.type = str(self.node.func_type)
        else:
            self.type = self.node.type

        logMsg = msg
        if self.node:
            msg = f"{self.type}: {msg}"
            logMsg = f"Node '{self.node.id}' returned error {msg}"

        super().__init__(msg)

        # if exc_info == True, this class must not be instantiated outside an `except:` clause
        LOGGER.debug(f"Error during importing nodetree. {logMsg}", exc_info=exc_info)


def _process_node_links(program, node: NodeN, ids) -> List[str]:
    links: Links = {}
    empty_links: List[str] = []

    link: Optional[LinkN]
    real_node = program.pipeline.nodes[node.id]

    for name in real_node.func_type.InputTypes.keys():
        input = node.inputs.get(name)

        try:
            if LINKS_INSTEAD_OF_INPUTS:
                link = input
            else:
                link = input.link

            if link.id not in ids:
                # Input link points to deleted node, so the key doesn't exist
                raise AttributeError

            links[name] = Connection(link.id, link.name)

        except AttributeError:  # input or link was None, or key didn't exist
            if LINKS_INSTEAD_OF_INPUTS:
                # there is no input.value to fall back on -> missing link
                raise NodeTreeImportError(
                    program, node, f"Missing input '{name}'", exc_info=False
                )

            empty_links.append(name)

    try:
        program.pipeline.create_links(node.id, links)
    except KeyError:  # idk why this happens
        raise NodeTreeImportError(program, msg="Unknown Error, please try again")

    # empty_links used by _process_node_inputs to select input.value
    return empty_links


def _process_widget(type: Type, val):
    if isinstance(type, RangeType):
        # Val is a Tuple[float, float]
        # Convert to Range
        val = type.create(**val)
    elif isinstance(type, Slide):
        # Val needs to be validated
        val = type.create(val)

    return val


def _process_node_inputs(program, node: NodeN, ids):
    empty_links = _process_node_links(program, node, ids)

    if LINKS_INSTEAD_OF_INPUTS:
        return

    # node.inputs : Dict[str, InputN]
    real_node = program.pipeline.nodes[node.id]

    for name in empty_links:
        type = real_node.func.InputTypes[name]
        # todo: will node.inputs[name].value ever be missing or invalid? if so, raise NodeImportError
        real_node.set_static_link(name, _process_widget(type, node.inputs[name].value))


def _process_node_settings(program, node: NodeN):
    if None in node.settings.values():
        raise NodeTreeImportError(
            program, node, "Cannot have None value in settings", exc_info=False
        )

    real_node = program.pipeline.nodes[node.id]
    real_node.pos = node.pos

    settings = {}

    try:
        for field in real_node.func_type.SettingTypes:
            if field.type is None:
                # field is disabled
                continue

            # throws KeyError on missing, ValueError on invalid
            settings[field.name] = _process_widget(
                field.type, node.settings[field.name]
            )

        # throws TypeError on missing
        settings = real_node.func_type.Settings(**settings)

        # throws ValueError on invalid
        settings = real_node.func_type.validate_settings(settings)

    except (KeyError, TypeError) as e:
        raise NodeTreeImportError(program, node, "Missing key in settings") from e

    except ValueError as e:
        raise NodeTreeImportError(program, node, "Invalid settings") from e

    if LINKS_INSTEAD_OF_INPUTS:
        restart = False
        if real_node.func_type.require_restart:
            if real_node.settings is not None:
                if not real_node.settings == settings:
                    restart = True
        try:
            if real_node.func.always_restart:
                restart = True
        except AttributeError:
            pass
        if restart:
            real_node.dispose()
        if real_node.func:
            real_node.func.settings = settings

    real_node.settings = settings


def _remove_unneeded_nodes(program, nodetree: NodeTreeN):
    visited = set()
    queue = deque()
    nodes = {}

    # First, add all sideeffect nodes to queue
    for node in nodetree.nodes:
        nodes[node.id] = node

        func = program.manager.funcs[node.type]
        if func.has_sideeffect:
            queue.append(node.id)

    # Then, do a DFS over queue, adding all reachable nodes to visited
    while queue:
        id = queue.pop()

        if id in visited:
            continue

        visited.add(id)

        for input in nodes[id].inputs.values():
            if LINKS_INSTEAD_OF_INPUTS:
                link = input
            else:
                link = input.link

            if link is None:
                continue

            queue.append(link.id)

    # Finally, remove those nodes that weren't visited
    nodes = [node for node in nodetree.nodes if node.id in visited]

    # make a copy of nodetree to fix broken json save
    nodetree = NodeTreeN(nodes=nodes)

    return nodetree


def import_nodetree(program, nodetree: NodeTreeN):
    nodetree = _remove_unneeded_nodes(program, nodetree)
    ids = [node.id for node in nodetree.nodes]

    # TODO : how to cache FifoLock in the stateless import_nodetree function?
    with FifoLock(program.queue):
        program.pipeline.prune_nodetree(ids)

        for node in nodetree.nodes:
            if node.id not in program.pipeline.nodes:
                try:
                    program.create_node(node.type, node.id)
                except KeyError as e:
                    raise NodeTreeImportError from e

        for node in nodetree.nodes:
            _process_node_settings(program, node)
            if LINKS_INSTEAD_OF_INPUTS:
                _process_node_links(program, node, ids)
            else:
                _process_node_inputs(program, node, ids)

            try:
                program.pipeline.nodes[node.id].ensure_init()
            except Exception as e:
                try:
                    del program.pipeline.nodes[node.id]
                except KeyError:
                    pass

                raise NodeTreeImportError(
                    program, node, "Error creating Function"
                ) from e

        try:
            program.pipeline.run()
            program.manager.pipeline_update()
        except Exception as e:
            program.pipeline.broken = True
            raise NodeTreeImportError(
                program,
                program.pipeline.current,
                f"Failed test run due to",
                real_node=True,
            )

        program.pipeline.broken = False
