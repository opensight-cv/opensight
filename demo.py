import uvicorn
from starlette.testclient import TestClient

from hbll.backend import Program
from hbll.backend.manager_schema import ModulePath
from hbll.webserver import WebServer


def make_program():
    program = Program()
    program.manager.register_module(ModulePath("modules", "six"))
    program.manager.register_module(ModulePath("modules", "seven"))

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
