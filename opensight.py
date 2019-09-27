#! /usr/bin/env python3

import asyncio
import json
import logging
import threading
from os import listdir
from os.path import dirname, isdir, isfile, join, splitext

import uvicorn
import uvloop
from starlette.testclient import TestClient

import opsi
from opsi.manager import Program
from opsi.manager.manager_schema import ModulePath
from opsi.webserver import WebServer
from opsi.webserver.schema import NodeTreeN
from opsi.webserver.serialize import import_nodetree

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def make_program(module_path):
    dir = join(module_path, "modules")
    program = Program()
    if isdir(dir):
        files = [splitext(f)[0] for f in listdir(dir) if isfile(join(dir, f))]
        for path in files:
            program.manager.register_module(ModulePath(dir, path))

    return program


def test_webserver(webserver):
    logger.info("Funcs: %s", webserver.get_funcs())
    logger.info("Nodes: %s", webserver.get_nodes())


# reimplementation of uvicorn.run without main-thread calls
async def run_app(app, **kwargs):
    config = uvicorn.Config(app, **kwargs)
    server = uvicorn.Server(config=config)

    config = server.config
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
    server.logger.info("Finished server process")


def create_threaded_loop():
    loop = uvloop.new_event_loop()
    threading.Thread(target=loop.run_forever).start()
    return loop


def main():
    package_path = dirname(opsi.__file__)
    program = make_program(package_path)

    webserver = WebServer(program, join(package_path, "frontend"))

    loop = create_threaded_loop()
    asyncio.run_coroutine_threadsafe(run_app(webserver.app, host="0.0.0.0"), loop)

    program.mainloop()


if __name__ == "__main__":
    main()
