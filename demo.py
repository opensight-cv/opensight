import uvicorn

from hbll.backend import Program
from hbll.backend.manager_schema import ModulePath
from hbll.webserver import WebServer


def main():
    program = Program()
    program.manager.register_module(ModulePath("modules", "six"))
    program.manager.register_module(ModulePath("modules", "seven"))

    webserver = WebServer(program)

    uvicorn.run(webserver.app)


if __name__ == "__main__":
    main()
