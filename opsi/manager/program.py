import logging
import queue
import threading
from threading import Thread
from uuid import UUID, uuid4

from ..util.persistence import PersistentNodetree
from ..webserver.schema import NodeTreeN
from ..webserver.serialize import import_nodetree
from .manager import Manager
from .pipeline import Node, Pipeline

logger = logging.getLogger(__name__)


class Program:
    def __init__(self, load_persist=True):
        self.queue = queue.Queue()
        self.persist = PersistentNodetree()

        self.manager = Manager()
        self.pipeline = Pipeline(self)

        self.p_thread = None

        if load_persist:
            self.load_persistence()

    def create_node(self, func_type: str, uuid: UUID = None) -> Node:
        if uuid is None:
            uuid = uuid4()

        func = self.manager.funcs[func_type]

        return self.pipeline.create_node(func, uuid)

    def load_persistence(self):
        nodetree = self.persist.nodetree

        if nodetree is not None:
            # queue import_nodetree to run at start of mainloop
            Thread(target=import_nodetree, args=(self, nodetree)).start()

    def mainloop(self, shutdown, lifespan):
        self.p_thread = threading.Thread(target=self.pipeline.mainloop)
        self.p_thread.name = "Pipeline Mainloop"
        self.p_thread.daemon = True
        self.shutdown = shutdown

        self.p_thread.start()

        while not self.shutdown.is_set():
            task = self.queue.get()  # todo: blocking & timeout?
            task.run()  # won't send exceptions because runs in seperate thead
        logger.info("Program main loop is shutting down...")
