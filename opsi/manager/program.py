import logging
import queue
import threading
from uuid import UUID, uuid4

from .manager import Manager
from .pipeline import Node, Pipeline


class Program:
    def __init__(self):
        self.queue = queue.Queue()

        self.manager = Manager()
        self.pipeline = Pipeline(self)

        self.p_thread = None

    def create_node(self, func_type: str, uuid: UUID = None) -> Node:
        if uuid is None:
            uuid = uuid4()

        func = self.manager.funcs[func_type]

        return self.pipeline.create_node(func, uuid)

    def mainloop(self):
        logger = logging.getLogger(__name__)

        self.p_thread = threading.Thread(target=self.pipeline.mainloop)
        self.p_thread.name = "Pipeline Mainloop"
        self.p_thread.daemon = True

        self.p_thread.start()

        while True:
            try:
                task = self.queue.get()  # todo: blocking & timeout?
                task.run()  # won't send exceptions because runs in seperate thead
            except Exception as e:
                logger.exception(e)
