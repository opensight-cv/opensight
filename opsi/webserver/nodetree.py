import dataclasses
import logging
import sys
import traceback
from typing import Dict, Tuple, Type

import networkx as nx

from opsi.manager.pipeline import Connection, Node
from opsi.manager.types import RangeType, Slide
from opsi.util.concurrency import FifoLock

LOGGER = logging.getLogger(__name__)


class NodeTreeImportError(Exception):
    def __init__(self, node=None, msg="", *, exc_info=True):
        self.node = None
        self.type = "unknown"

        if isinstance(node, Node):
            self.node, self.type = node.id, node.func_type.type
        elif node is not None:  # graph.nodes[id]
            self.node, self.type = node["id"], node.type

        self.traceback = ""

        # if exc_info: autodetect if called in except clause; set exc_info=False to force disable
        if exc_info and sys.exc_info()[0] is not None:
            exc_info = sys.exc_info()

            msg += f": {exc_info[1]!r}"
            self.traceback = traceback.format_tb(exc_info[2])

        logMsg = msg
        if self.node:
            msg = f"{self.type}: {msg}"
            logMsg = f"Node '{self.node}' returned error {msg}"

        super().__init__(msg)

        LOGGER.debug(f"Error during importing nodetree. {logMsg}", exc_info=exc_info)


# Convention: the direction of an edge goes from right-to-left


def get_node_values(node: "NodeN") -> Tuple[str, Dict]:
    data = {
        "connections": {},
        "static_links": {
            input_name: input.value
            for input_name, input in node.inputs.items()
            if input.link is None
        },
        **dict(node),
    }

    return (node.id, data)


def create_graph(nodetree: "NodeTreeN") -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()

    nodes = map(get_node_values, nodetree.nodes)
    graph.add_nodes_from(nodes)
    existing_nodes = set(graph.nodes)

    # (right, left, data)
    edges = (
        (node.id, input.link.id, {"left": input.link.name, "right": input_name})
        for node in nodetree.nodes
        for input_name, input in node.inputs.items()
        if input.link is not None
    )
    graph.add_edges_from(edges)
    new_nodes = set(graph.nodes)

    added_nodes = new_nodes - existing_nodes
    if len(added_nodes):
        # add_edges_from() automatically added new nodes that weren't in add_nodes_from()
        raise NodeTreeImportError(
            msg=f"Input links reference nonexistent nodes: {list(added_nodes)}"
        )

    if not nx.algorithms.dag.is_directed_acyclic_graph(graph):
        raise NodeTreeImportError(msg="Graph has a cycle")

    return graph


def remove_unreachable_nodes(graph):
    sideeffect_nodes = (
        id for id, node in graph.nodes.items() if node["func_type"].has_sideeffect
    )

    reachable = set().union(
        *(
            nx.algorithms.dag.descendants(graph, node) | {node}
            for node in sideeffect_nodes
        )
    )

    unreachable = graph.nodes - reachable

    graph.remove_nodes_from(unreachable)


def _process_widget(type: Type, val):
    if isinstance(type, RangeType):
        # Val is a Tuple[float, float]
        # Convert to Range
        val = type.create(**val)
    elif isinstance(type, Slide):
        # Val needs to be validated
        val = type.create(val)

    return val


def create_connections(graph):
    for (right_node, left_node, _), names in graph.edges.items():
        print(
            f"connect L {left_node} {names['left']} to R {right_node} {names['right']}"
        )

        # TODO: verify names exist, type compatible

        graph.nodes[right_node]["connections"][names["right"]] = Connection(
            left_node, names["left"]
        )


def create_static_links(node):
    for name, value in node["static_links"].items():
        type = node["func_type"].InputTypes[name]
        # todo: will node.inputs[name].value ever be missing or invalid? if so, raise NodeImportError
        if value is None:
            raise NodeTreeImportError(f"Missing input '{name}'")
        node["static_links"][name] = _process_widget(type, value)


def create_settings(node):
    if None in node["settings"].values():
        raise NodeTreeImportError(node, "Cannot have None value in settings")

    settings = {}

    try:
        for field in node["func_type"].SettingTypes:
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
                setting = _process_widget(field.type, node["settings"][field.name])
            except KeyError:
                default = field.default
                if default is not dataclasses.MISSING:
                    setting = default
                else:
                    # TODO: create table for default values (of all widget types?) (e.g. int - 0)
                    raise

            settings[field.name] = setting

        # throws TypeError on missing
        settings = node["func_type"].Settings(**settings)

        # throws ValueError on invalid
        settings = node["func_type"].validate_settings(settings)

    except (KeyError, TypeError):
        raise NodeTreeImportError(node, "Missing key in settings")

    except ValueError:
        raise NodeTreeImportError(node, "Invalid settings")

    node["settings"] = settings


def get_separate_graphs(graph):  # TODO: use for split pipelines
    return (
        graph.subgraph(nodes)
        for nodes in nx.algorithms.components.connected_components(
            graph.to_undirected(as_view=True)
        )
    )


class Importer:
    def __init__(self, program):
        self.program = program
        self.lock = FifoLock(program.queue)

    def lookup_funcs(self, graph):
        for node in graph.nodes.values():
            try:
                func_type = self.program.manager.funcs[node["type"]]
            except KeyError:
                raise NodeTreeImportError("Could not find function")
            node["func_type"] = func_type

    def apply_nodetree(self, graph):
        self.program.pipeline.hard_reset()

        entries = []
        for node_data in graph.nodes.values():
            node = self.program.pipeline.create_node(
                node_data["func_type"], node_data["id"]
            )
            node.set_static_links(node_data["static_links"])

            entries.append((node, node_data))

        for node, node_data in entries:
            self.program.pipeline.create_links(node.id, node_data["connections"])

    def import_nodetree(self, nodetree: "NodeTreeN"):
        graph = create_graph(nodetree)
        self.lookup_funcs(graph)
        remove_unreachable_nodes(graph)

        for node in graph.nodes.values():
            create_settings(node)
            create_static_links(node)

        create_connections(graph)

        with self.lock:
            print("import lol")
            print(graph)
            self.apply_nodetree(graph)


if True:
    try:
        from unittest.mock import MagicMock, Mock

        import opsi
        from opsi.lifespan.lifespan import Program, register_modules

        from .schema import NodeTreeN

        globals()["NT"] = NodeTreeN.parse_file("sample2.json")

        globals()["program"] = Program(Mock())
        program.importer.lock = MagicMock()
        register_modules(program, opsi.__file__)

        globals()["graph"] = program.import_nodetree(NT)
    except:
        import sys
        import traceback

        traceback.print_exception(*sys.exc_info())
