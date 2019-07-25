from uuid import uuid4

from hbll.backend.manager import Manager
from hbll.backend.manager_schema import ModulePath
from hbll.backend.pipeline import Connection
from hbll.backend.pipeline_recursive import RecursivePipeline


def main():
    manager = Manager()
    manager.register_module(ModulePath("modules", "five"))
    print(manager)

    pipeline = RecursivePipeline()

    node_five = pipeline.create_node(manager.funcs["demo.five/Five"], uuid4())
    node_sum = pipeline.create_node(manager.funcs["demo.five/Sum"], uuid4())
    node_print = pipeline.create_node(manager.funcs["demo.five/Print"], uuid4())

    pipeline.create_links(node_sum, {"num1": Connection(node_five, "five")})
    node_sum.set_staticlinks({"num2": 10})

    pipeline.create_links(node_print, {"val": Connection(node_sum, "out")})

    pipeline.run()


if __name__ == "__main__":
    main()
