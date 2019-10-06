import asyncio
import logging
import signal
import threading
import time
from os import listdir
from os.path import dirname, isdir, isfile, join, splitext

import uvloop

import opsi
from opsi.manager import Program
from opsi.manager.manager_schema import ModulePath
from opsi.util.persistence import PersistentNodetree
from opsi.webserver import WebServer

from ..webserver.serialize import import_nodetree
from .threadserver import ThreadedWebserver

LOGGER = logging.getLogger(__name__)


def register_modules(program, module_path):
    moddir = join(module_path, "modules")
    if isdir(moddir):
        files = [splitext(f)[0] for f in listdir(moddir) if isfile(join(moddir, f))]
        for path in files:
            program.manager.register_module(ModulePath(moddir, path))


class Lifespan:
    def __init__(self, args, catch_signal=False, load_persist=True):
        self.event = threading.Event()
        self.threads = []
        self.restart = True

        self.program = Program(self)
        self.args = args
        self.persist = PersistentNodetree(path=args.persist)

        if catch_signal:
            signal.signal(signal.SIGINT, self.catch_signal)
            signal.signal(signal.SIGTERM, self.catch_signal)

        if load_persist:
            self.load_persistence()

    def load_persistence(self):
        nodetree = self.persist.nodetree

        if nodetree is not None:
            # queue import_nodetree to run at start of mainloop
            threading.Thread(
                target=import_nodetree, args=(self.program, nodetree)
            ).start()

    def __create_threaded_loop__(self):
        loop = uvloop.new_event_loop()
        thread = threading.Thread(target=loop.run_forever)
        thread.daemon = True
        thread.start()
        self.threads.append(thread)
        return loop

    def __create_thread__(self, target):
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        self.threads.append(thread)
        return thread

    def make_threads(self):
        path = dirname(opsi.__file__)
        register_modules(self.program, path)
        self.__create_thread__(self.program.mainloop)

        ws = WebServer(self.program, join(path, "frontend"))
        webserver = ThreadedWebserver(
            self.event, ws.app, host="0.0.0.0", port=self.args.port or ws.port
        )
        ws_loop = self.__create_threaded_loop__()
        asyncio.run_coroutine_threadsafe(webserver.run(), ws_loop)

    def main_loop(self):
        while self.restart:
            LOGGER.info("OpenSight starting...")
            self.event.clear()
            self.make_threads()
            self.event.wait()
            for thread in self.threads:
                thread.join()
            LOGGER.info("OpenSight successfully shutdown.")

    def catch_signal(self, signum, frame):
        self.shutdown()

    def shutdown(self, restart=False):
        LOGGER.info("Waiting for threads to shut down...")
        self.event.set()
        self.restart = restart
