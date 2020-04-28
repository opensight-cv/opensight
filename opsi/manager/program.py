import logging
import queue
import threading

from .manager import Manager
from .pipeline import Node, Pipeline

LOGGER = logging.getLogger(__name__)


class Program:
    def __init__(self, lifespan):
        self.queue = queue.Queue()
        self.lifespan = lifespan

        self.pipeline = Pipeline(self)
        self.manager = Manager(self.pipeline)

        self.p_thread = None

    def create_node(self, func_type: str, uuid: str) -> Node:
        try:
            func = self.manager.funcs[func_type]
        except KeyError:
            raise ValueError(f"Function {func_type} not found")

        return self.pipeline.create_node(func, uuid)

    def mainloop(self, shutdown):
        self.shutdown = shutdown

        self.p_thread = threading.Thread(target=self.pipeline.mainloop)
        self.p_thread.name = "Pipeline Mainloop"
        self.p_thread.daemon = True

        self.p_thread.start()

        while not self.shutdown.is_set():
            task = self.queue.get()  # todo: blocking & timeout?
            task.run()  # won't send exceptions because runs in seperate thead
        LOGGER.info("Program main loop is shutting down...")
        self.pipeline.dispose_all()
        self.pipeline.clear()
        self.manager.shutdown()
        self.shutdown.clear()
