#! /usr/bin/env python3

import uvicorn
from starlette.testclient import TestClient

from os import listdir
from os.path import isdir, isfile, join, splitext

from opsi.backend import Program
from opsi.backend.manager_schema import ModulePath
from opsi.webserver import WebServer


def make_program():
    program = Program()
    if isdir("modules"):
        files = [
            splitext(f)[0] for f in listdir("modules") if isfile(join("modules", f))
        ]
        for path in files:
            program.manager.register_module(ModulePath("modules", path))
    # program.manager.register_module(ModulePath("/usr/share/opensight/modules", "six"))
    # program.manager.register_module(ModulePath("/usr/share/opensight/modules", "seven"))
    return program


def make_nodetree(program):
    func_type = "demo.seven/IsInRange"
    func = program.manager.funcs[func_type]

    settings = func.Settings(range=func.SettingTypes["range"].create(10, 70))

    node = program.create_node(func_type)
    node.settings = settings
    node.set_staticlinks({"num": 20})


def test_webserver(webserver):
    print()
    print(webserver.get_funcs())
    print()
    print(webserver.get_nodes())
    print()


def main():
    program = make_program()

    make_nodetree(program)

    program.pipeline.run()

    webserver = WebServer(program)

    test_webserver(webserver)

    uvicorn.run(webserver.app)


if __name__ == "__main__":
    main()
