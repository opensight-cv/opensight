import time
import threading
import logging

from opsi.lifespan.lifespan import Lifespan

logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)


def test_webserver(webserver):
    LOGGER.info("Funcs: %s", webserver.get_funcs())
    LOGGER.info("Nodes: %s", webserver.get_nodes())


def main():
    lifespan = Lifespan()
    lifespan.make_threads()


if __name__ == "__main__":
    main()
