import logging
import os
import signal
import subprocess
import threading
from os.path import isdir, isfile, splitext

import opsi
from opsi.backend.network import dhcpcd_writable
from opsi.manager import Program
from opsi.manager.manager_schema import ModulePath
from opsi.util.concurrency import ShutdownThread
from opsi.util.networking import choose_port
from opsi.util.path import join
from opsi.util.persistence import Persistence
from opsi.webserver.app import WebServer
from opsi.webserver.serialize import import_nodetree

from .webserverthread import WebserverThread

# import optional dependencies

try:
    from pystemd.systemd1 import Unit

    PYSTEMD_AVAIL = True
except ImportError:
    PYSTEMD_AVAIL = False


LOGGER = logging.getLogger(__name__)


IGNORE_FOLDERS = {"disabled", "__pycache__"}


def register_modules(program, module_path):
    moddir = join(module_path, "modules") + "/"
    if not isdir(moddir):
        return

    for path in os.listdir(moddir):
        fullpath = join(moddir, path)

        if isfile(fullpath):
            path = splitext(path)[0]
        elif not (isdir(fullpath) and path.strip().lower() not in IGNORE_FOLDERS):
            continue

        program.manager.register_module(ModulePath(moddir, path))


class Lifespan:
    PORTS = (80, 8000)

    def __init__(self, args, *, catch_signal=False, load_persist=True, timeout=10):
        self.event = threading.Event()
        self.threads = []

        self._restart = True

        self.timer = threading.Timer(timeout, self.terminate)

        self._systemd = None
        self._unit = None
        self._netconf = None

        self.ports = args.port or self.PORTS
        self.persist = Persistence(path=args.persist) if load_persist else None

        if catch_signal:
            self.signalCount = 0
            signal.signal(signal.SIGINT, self.catch_signal)
            signal.signal(signal.SIGTERM, self.catch_signal)

    def load_persistence(self, program):
        nodetree = self.persist.nodetree

        if nodetree is not None:
            # queue import_nodetree to run at start of mainloop
            threading.Thread(
                target=import_nodetree,
                args=(program, nodetree),
                kwargs={"force_save": True},
            ).start()

    @property
    def using_systemd(self):
        if not PYSTEMD_AVAIL:
            return False
        if self._systemd is not None:
            return self._systemd
        self._unit = Unit(b"opensight.service", _autoload=True)
        self._systemd = self._unit.Unit.ActiveState == b"active"
        return self._systemd

    @property
    def netconf_writable(self):
        if self._netconf is not None:
            return self._netconf
        self._netconf = self.using_systemd and dhcpcd_writable()
        return self._netconf

    def make_threads(self):
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
        while self._restart:
            LOGGER.info(f"OpenSight starting... version {opsi.__version__}")
            self.event.clear()
            self.make_threads()
            self.event.wait()
            for thread in self.threads:
                LOGGER.debug("Shutting down %s", thread.name)
                thread.shutdown()
            self.timer.cancel()
            LOGGER.info("OpenSight successfully shutdown.")

    def catch_signal(self, signum, frame):
        self.shutdown()
        self.signalCount += 1
        if self.signalCount >= 2:
            self.terminate()

    def terminate(self):
        LOGGER.critical("OpenSight failed to close gracefully! Terminating...")
        os.kill(os.getpid(), signal.SIGKILL)

    def shutdown_threads(self):
        if not self._restart:
            if not self.timer.is_alive():
                try:
                    self.timer.start()
                except RuntimeError:
                    pass
        LOGGER.info("Waiting for threads to shut down...")
        self.event.set()

    def restart(self, host=False):
        if host:
            self._restart = False
            self.shutdown_threads()
            subprocess.Popen("reboot", shell=True)
            return
        if self.using_systemd:
            self._restart = False
            self.shutdown_threads()
            return
        self._restart = True
        self.shutdown_threads()

    def shutdown(self, host=False):
        self._restart = False
        self.shutdown_threads()
        if host:
            subprocess.Popen("shutdown now", shell=True)
            return
        if self.using_systemd:
            self._unit.Stop(b"replace")
            return
