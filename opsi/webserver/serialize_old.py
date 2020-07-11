import logging
import sys
import traceback
from collections import deque
from dataclasses import MISSING, fields
from typing import Callable, Dict, List, Optional, Tuple, Type

from opsi.manager.manager import Manager
from opsi.manager.manager_schema import Function, ModuleItem
from opsi.manager.pipeline import Connection, Links
from opsi.manager.types import AnyType, RangeType, Slide
from opsi.util.concurrency import FifoLock

from .schema import FunctionF, InputOutputF, ModuleF, SchemaF

LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------


def _rangetype_serialize(type):
    if not isinstance(type, RangeType):
        return None

    return InputOutputF(type="Range", params=type.serialize())


def _slide_serialize(type):
    if not isinstance(type, Slide):
        return None

    return InputOutputF(type="Slide", params=type.serialize())


def _tuple_serialize(type):
    if not isinstance(type, tuple):
        return None

    return InputOutputF(type="Enum", params={"items": type})


_type_name: Dict[Type, str] = {AnyType: "Any"}
# Each item in _abnormal_types takes in a type and returns InputOutputF if the
# parser supports the type, or None if it does not
_abnormal_types: List[Callable[[Type[any]], Optional[InputOutputF]]] = [
    _slide_serialize,
    _rangetype_serialize,
    _tuple_serialize,
]  # add new type parsers here


def get_type(_type: Type) -> InputOutputF:
    if _type in (None, type(None)):
        return None

    if _type in _type_name:
        name = _type_name.get(_type)
        return InputOutputF(type=name)

    for parser in _abnormal_types:
        IO = parser(_type)

        if IO is not None:
            return IO

    return InputOutputF(type=_type.__name__)


def get_field_type(field) -> InputOutputF:
    io = get_type(field.type)
    if field.default and field.default is not MISSING:
        io.params["default"] = field.default
    return io


def get_types(types):
    # there are no instances of an input or output having type None
    return {name: get_type(_type) for name, _type in types.items()}


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
            inputs=get_types(func.InputTypes),
            outputs=get_types(func.OutputTypes),
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
    return SchemaF(modules=_serialize_modules(manager.modules))


# ---------------------------------------------------------


class NodeTreeImportError(Exception):
    def __init__(
        self, program, node: "NodeN" = None, msg="", *, exc_info=True, real_node=None,
    ):
        program.pipeline.clear()
        program.pipeline.broken = True

        self.node = node
        self.traceback = ""

        # https://github.com/python/cpython/blob/10ecbadb799ddf3393d1fc80119a3db14724d381/Lib/logging/__init__.py#L1572
        if exc_info:
            if isinstance(exc_info, BaseException):
                exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
            elif not isinstance(exc_info, tuple):
                exc_info = sys.exc_info()

            msg += f": {exc_info[1]!r}"
            self.traceback = traceback.format_tb(exc_info[2])

        self.type = "unknown"
        if self.node:
            self.type = self.node.type
        elif real_node:
            self.type = real_node.func_type

        logMsg = msg
        if self.node:
            msg = f"{self.type}: {msg}"
            logMsg = f"Node '{self.node.id}' returned error {msg}"

        super().__init__(msg)

        # if exc_info == True, this class must not be instantiated outside an `except:` clause
        LOGGER.debug(f"Error during importing nodetree. {logMsg}", exc_info=exc_info)


def _process_node_links(program, node: "NodeN", ids) -> List[str]:
    links: Links = {}
    empty_links: List[str] = []

    real_node = program.pipeline.nodes[node.id]

    for name in real_node.func_type.InputTypes.keys():
        input = node.inputs.get(name)

        try:
            if input.link.id in ids:
                links[name] = Connection(input.link.id, input.link.name)
            else:
                # link was None, or link points to deleted node
                empty_links.append(name)
        except AttributeError:
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


def _process_node_inputs(program, node: "NodeN", ids):
    empty_links = _process_node_links(program, node, ids)

    real_node = program.pipeline.nodes[node.id]

    for name in empty_links:
        type = real_node.func_type.InputTypes[name]
        # todo: will node.inputs[name].value ever be missing or invalid? if so, raise NodeImportError
        if node.inputs[name].value is None:
            raise NodeTreeImportError(
                program, node, f"Missing input '{name}'", exc_info=False
            )
        real_node.set_static_link(name, _process_widget(type, node.inputs[name].value))


def _process_node_settings(program, node: "NodeN"):
    if None in node.settings.values():
        raise NodeTreeImportError(
            program, node, "Cannot have None value in settings", exc_info=False
        )

    real_node = program.pipeline.nodes[node.id]
    defaults = {x.name: x.default for x in fields(real_node.func_type.Settings)}

    settings = {}

    try:
        for field in real_node.func_type.SettingTypes:
            if field.type is None:
                # field is disabled
                continue

            # throws ValueError on invalid
            # try the following before giving up:
            # 1. Use the value provided by the nodetree
            # 2. If none provided by nodetree, get default value for element in dataclass
            # 3. If no default, try default initializing the type
            # 4. If can't default initialize type, give up
            try:
                setting = _process_widget(field.type, node.settings[field.name])
            except KeyError:
                default = defaults[field.name]
                if default is not MISSING:
                    setting = default
                else:
                    # TODO: create table for default values (of all widget types?) (e.g. int - 0)
                    raise

            settings[field.name] = setting

        # throws TypeError on missing
        settings = real_node.func_type.Settings(**settings)

        # throws ValueError on invalid
        settings = real_node.func_type.validate_settings(settings)

    except (KeyError, TypeError):
        raise NodeTreeImportError(program, node, "Missing key in settings")

    except ValueError:
        raise NodeTreeImportError(program, node, "Invalid settings")

    if (
        (real_node.func_type.require_restart)  # restart only on changed settings
        and (real_node.settings is not None)
        and (not real_node.settings == settings)
    ) or real_node.func_type.always_restart:  # or if force always
        real_node.dispose()

    if real_node.func:
        real_node.func.settings = settings

    real_node.settings = settings


def _remove_unneeded_nodes(program, nodetree: "NodeTreeN") -> Tuple["NodeTreeN", bool]:
    visited = set()
    queue = deque()
    nodes = {}

    # First, add all sideeffect nodes to queue
    for node in nodetree.nodes:
        nodes[node.id] = node

        try:
            func = program.manager.funcs[node.type]
            if func.has_sideeffect:
                queue.append(node.id)
        except KeyError:
            # if function doesn't exist
            raise NodeTreeImportError(program, node, "Unknown function")

    # Then, do a DFS over queue, adding all reachable nodes to visited
    while queue:
        id = queue.pop()

        if id in visited:
            continue

        visited.add(id)

        for input in nodes[id].inputs.values():
            link = input.link

            if link is None:
                continue

            queue.append(link.id)

    # Finally, remove those nodes that weren't visited
    nodes = [node for node in nodetree.nodes if node.id in visited]

    # make a copy of nodetree to fix broken json save
    nodetree = nodetree.copy(update={"nodes": nodes})

    # return nodetree and report no broken nodes
    return nodetree


def import_nodetree(program, nodetree: "NodeTreeN", force_save: bool = False):
    original_nodetree = nodetree
    nodetree = _remove_unneeded_nodes(program, nodetree)
    ids = [node.id for node in nodetree.nodes]

    # TODO : how to cache FifoLock in the stateless import_nodetree function?
    with FifoLock(program.queue):
        program.pipeline.prune_nodetree(ids)

        for node in nodetree.nodes:
            if node.id not in program.pipeline.nodes:
                try:
                    program.create_node(node.type, node.id)
                except KeyError:
                    raise NodeTreeImportError

        for node in nodetree.nodes:
            try:
                _process_node_settings(program, node)
                _process_node_inputs(program, node, ids)
            except NodeTreeImportError:
                raise
            except Exception:
                if not force_save:
                    raise NodeTreeImportError(program, node, "Error processing node")

            try:
                program.pipeline.nodes[node.id].ensure_init()
            except Exception:
                try:
                    del program.pipeline.nodes[node.id]
                except KeyError:
                    pass

                if not force_save:
                    raise NodeTreeImportError(program, node, "Error creating Function")

        try:
            program.pipeline.run()
            program.manager.pipeline_update()
        except Exception:
            program.pipeline.broken = True
            if force_save:
                program.lifespan.persist.nodetree = original_nodetree
            raise NodeTreeImportError(
                program,
                real_node=program.pipeline.current,
                msg="Failed test run due to",
            )

        program.lifespan.persist.nodetree = original_nodetree
        program.pipeline.broken = False
