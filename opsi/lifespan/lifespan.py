import threading
import asyncio
import logging
import time

from os import listdir
from os.path import dirname, isdir, isfile, join, splitext

import uvicorn
import uvloop

import opsi
from opsi.manager.manager_schema import ModulePath
from opsi.manager import Program
from opsi.webserver import WebServer


LOGGER = logging.getLogger(__name__)


def make_program(module_path):
    moddir = join(module_path, "modules")
    program = Program()
    if isdir(moddir):
        files = [splitext(f)[0] for f in listdir(moddir) if isfile(join(moddir, f))]
        for path in files:
            program.manager.register_module(ModulePath(moddir, path))
    return program


async def manage_webserver(event, app, **kwargs):
    loop = asyncio.get_event_loop()
    config = uvicorn.Config(app, **kwargs)
    server = uvicorn.Server(config=config)
    server_event = threading.Event()

    # run webserver until shutdown event
    asyncio.run_coroutine_threadsafe(run_app(server_event, config, server), loop)
    while not event.is_set():
        await asyncio.sleep(0.1)

    # wait until server stops gracefully before stopping loop
    server.should_exit = True
    while not server_event.is_set():
        await asyncio.sleep(0.1)
    await loop.stop()


async def run_app(event, config, server):
    if not config.loaded:
        config.load()

    server.logger = config.logger_instance
    server.lifespan = config.lifespan_class(config)

    server.logger.info("Started server process")
    await server.startup()
    if server.should_exit:
        return
    await server.main_loop()
    await server.shutdown()
    event.set()
    server.logger.info("Finished server process")


class Lifespan:
    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.threads = []

    def __create_threaded_loop__(self):
        loop = uvloop.new_event_loop()
        thread = threading.Thread(target=loop.run_forever)
        thread.start()
        self.threads.append(thread)
        return loop

    def __create_thread__(self, target):
        loop = uvloop.new_event_loop()
        thread = threading.Thread(target=target, args=(self.shutdown_event, self))
        thread.start()
        self.threads.append(thread)
        return loop

    def make_threads(self):
        package_path = dirname(opsi.__file__)

        program = make_program(package_path)
        webserver = WebServer(program, join(package_path, "frontend"))

        ws_loop = self.__create_threaded_loop__()
        asyncio.run_coroutine_threadsafe(
            manage_webserver(self.shutdown_event, webserver.app, host="0.0.0.0"),
            ws_loop,
        )

        self.__create_thread__(program.mainloop)

    def shutdown(self):
        LOGGER.info("Shutting program down...")
        self.shutdown_event.set()
        for thread in self.threads:
            thread.join()
        LOGGER.info("OpenSight successfully shutdown.")
