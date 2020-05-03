import logging
from itertools import chain
from queue import deque
from typing import Any, Dict, List, NamedTuple, Optional, Set, Type

from toposort import toposort

from opsi.util.concurrency import FifoLock
from opsi.util.fps import FPS

from .link import Link, NodeLink, StaticLink
from .manager_schema import Function, Hook
from .netdict import NT_AVAIL, NetworkTables

LOGGER = logging.getLogger(__name__)


# Map inputname -> (output_node, output_name)
class Connection(NamedTuple):
    id: str
    name: str


Links = Dict[str, Connection]


class Node:
    def __init__(self, func: Type[Function], id: str):
        self.func_type = func
        self.inputLinks: Dict[str, Link] = dict()
        self.func: Optional[Function] = None
        self.id = id

        self.results = None
        self.has_run: bool = False
        self.skip: bool = False

        self.settings = None

    def next_frame(self):
        self.results = None
        self.has_run = False

    def reset_links(self):
        self.inputLinks.clear()

    def ensure_init(self):
        if self.func is not None:
            return

        self.func = self.func_type(self.settings)

    def dispose(self):
        if self.func is None:
            return

        try:
            self.func.dispose()
        except:
            msg = f"Error while disposing node f{self.func_type.type}"
            LOGGER.error(msg, exc_info=True)
        finally:
            self.func = None

    def set_static_link(self, key: str, item: Any):
        self.inputLinks[key] = StaticLink(item)

    def set_static_links(self, vals: Dict[str, Any]):
        for key, item in vals.items():
            self.set_static_link(key, item)

    def run(self):
        if self.has_run:
            return self.results

        self.ensure_init()

        fieldCount = len(self.func_type.InputTypes)
        inputs = {name: link.get() for name, link in self.inputLinks.items()}
        if fieldCount > len(inputs):
            self.results = None
            self.has_run = True
            return

        inputs = self.func_type.Inputs(**inputs)
        self.results = self.func.run(inputs)

        if self.results is None:
            try:
                self.results = self.func.Outputs()
            except TypeError:  # Outputs has some fields which do not have defaults
                LOGGER.error(
                    f"Function {self.func_type.type} cannot return None if there is no default Output"
                )

        self.has_run = True

        return self.results


class Pipeline:
    def __init__(self, program):
        self.program = program
        self.nodes: Dict[id, Node] = {}
        self.adjList: Dict[Node, Set[Node]] = {}
        self.run_order: List[Node] = []
        self.lock = FifoLock(self.program.queue)
        self.broken = False
        self.current: Optional[Node] = None
        self.fps = FPS()

        self.hook = Hook()
        self.hook.pipeline = self

    def run(self):
        if self.broken:
            return

        if not self.run_order:
            self.run_order = list(chain.from_iterable(toposort(self.adjList)))

        for n in self.run_order:  # Each node to be processed
            n.next_frame()
            self.current = n
            if not n.skip:
                try:
                    n.run()
                except Exception:
                    self.hook.cancel_current()
                    LOGGER.exception(
                        f"Error while running node {n.func_type.__name__}",
                        exc_info=True,
                    )

            n.skip = False

    def mainloop(self):
        while True:
            try:
                with self.lock:
                    self.run()
                if NT_AVAIL:
                    NetworkTables.flush()

            except (TypeError, AttributeError):
                LOGGER.debug(
                    "(Harmless?) Error during pipeline mainloop", exc_info=True
                )
            except:  # todo: wildcard except
                LOGGER.exception("Error during pipeline mainloop")

            self.fps.update()

    def get_dependents(self, node):
        visited = set()
        queue = deque()
        path = {}

        # First, add all side effect nodes to queue
        for id, i in self.nodes.items():
            if i.func_type.has_sideeffect:
                queue.append(id)

        # Then, do a DFS over queue, adding all reachable nodes to visited
        # Store children in map, creating a "path"
        while queue:
            id = queue.pop()

            if id in visited:
                continue
            if id == node.id:
                break

            for input in self.nodes[id].inputLinks.values():
                link = input
                if link is None:
                    continue
                queue.append(link.node.id)
                path[link.node] = self.nodes[id]

        pathTemp = node
        skip_nodes = []
        while pathTemp is not None:
            # Don't skip supplied node, since that would be applied next run
            # if pathTemp is not node:
            skip_nodes.append(pathTemp)
            pathTemp = path.get(pathTemp)
        return skip_nodes

    def cancel_nodes(self, nodes):
        for node in nodes:
            node.skip = True

    # def cancel_dependents(self, node, path):
    # Iterate through path and skip all nodes which were visited

    def create_node(self, func: Type[Function], uuid: str):
        """
        The caller is responsible for calling
        pipeline.create_links(node, ...) and node.set_staticlinks(...),
        and setting node.settings as appropriate
        """
        self.run_order.clear()
        temp = Node(func, uuid)

        self.adjList[temp] = set()
        self.nodes[uuid] = temp

        return temp

    def create_links(self, input_node_id, links: Links):
        self.run_order.clear()
        input_node = self.nodes[input_node_id]

        for input_name, conn in links.items():
            output_node = self.nodes[conn.id]
            self.adjList[input_node].add(output_node)

            input_node.inputLinks[input_name] = NodeLink(output_node, conn.name)

    def clear(self):
        self.run_order.clear()
        for node in self.nodes.values():
            node.reset_links()

    def dispose_all(self):
        for node in self.nodes.values():
            node.dispose()

    def prune_nodetree(self, new_node_ids):
        old_node_ids = set(self.nodes.keys())
        new_node_ids = set(new_node_ids)
        removed = old_node_ids - new_node_ids

        self.clear()
        # remove deleted nodes
        for uuid in removed:
            try:
                self.nodes[uuid].dispose()
                del self.adjList[self.nodes[uuid]]
                del self.nodes[uuid]
            except KeyError:
                pass
