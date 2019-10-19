import asyncio
import logging
import signal
import threading
from os import listdir
from os.path import isdir, isfile, splitext

import uvloop
from networktables import NetworkTables
from pystemd.systemd1 import Unit

import opsi
from opsi.manager import Program
from opsi.manager.manager_schema import ModulePath
from opsi.util.concurrency import AsyncThread, ShutdownThread
from opsi.util.networking import choose_port, get_nt_server
from opsi.util.path import join
from opsi.util.persistence import Persistence
from opsi.webserver import WebServer
from opsi.webserver.serialize import import_nodetree

from .webserverthread import WebserverThread

LOGGER = logging.getLogger(__name__)


def register_modules(program, module_path):
    moddir = join(module_path, "modules") + "/"
    if isdir(moddir):
        files = [splitext(f)[0] for f in listdir(moddir) if isfile(join(moddir, f))]
        for path in files:
            program.manager.register_module(ModulePath(moddir, path))


def init_networktables(network):
    if network["nt-client"]:
        addr = get_nt_server(network)
        NetworkTables.initialize(server=addr)
    else:
        NetworkTables.initialize()


class Lifespan:
    PORTS = (80, 8000)

    def __init__(self, args, *, catch_signal=False, load_persist=True):
        self.event = threading.Event()
        self.threads = []
        self.restart = True

        self._systemd = None

        self.ports = args.port or self.PORTS
        self.persist = Persistence(path=args.persist) if load_persist else None

        if catch_signal:
            signal.signal(signal.SIGINT, self.catch_signal)
            signal.signal(signal.SIGTERM, self.catch_signal)

    def load_persistence(self, program):
        nodetree = self.persist.nodetree

        if nodetree is not None:
            # queue import_nodetree to run at start of mainloop
            threading.Thread(target=import_nodetree, args=(program, nodetree)).start()

    @property
    def using_systemd(self):
        if self._systemd:
            return self._systemd
        unit = Unit(b"opensight.service", _autoload=True)
        self._systemd = unit.Unit.ActiveState == b"active"
        return self._systemd

    def make_threads(self):
        if self.persist.network["nt-enabled"]:
            init_networktables(self.persist.network)

        program = Program(self)

        path = opsi.__file__
        register_modules(program, path)

        # self.__create_thread__(program.mainloop)
        self.threads.append(
            ShutdownThread(program.mainloop, name="Program thread", autostart=True)
        )

        port = choose_port(self.ports)
        if not port:
            if isinstance(self.ports, tuple):
                msg = f"Unable to bind to any of ports {self.ports}"
            else:
                msg = f"Unable to bind to port {self.ports}"
            LOGGER.critical(msg)
            self.shutdown()
            return

        webserver = WebServer(program, join(path, "frontend"), port)
        self.threads.append(WebserverThread(webserver.app, host="0.0.0.0", port=port))

        if self.persist:
            self.load_persistence(program)

    def main_loop(self):
        while self.restart:
            LOGGER.info("OpenSight starting...")
            self.event.clear()
            self.make_threads()
            self.event.wait()
            for thread in self.threads:
                LOGGER.debug("Shutting down %s", thread.name)
                thread.shutdown()
            LOGGER.info("OpenSight successfully shutdown.")

    def catch_signal(self, signum, frame):
        self.shutdown()

    def shutdown(self, restart=False, host=False):
        if self.persist.network["nt-enabled"]:
            NetworkTables.shutdown()
        LOGGER.info("Waiting for threads to shut down...")
        self.event.set()
        self.restart = restart
        if host:
            self.restart = False
            if restart:
                subprocess.Popen("reboot", shell=True)
            else:
                subprocess.Popen("shutdown now".split(), shell=True)
