#!/usr/bin/env python3
import logging
import argparse

from opsi.lifespan.lifespan import Lifespan

logging.basicConfig(level=logging.ERROR)
LOGGER = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument(
    "-n", "--node-persist", dest="persist", help="location to store nodetree pipeline"
)
parser.add_argument("-p", "--port", dest="port", help="port to run webserver on")


def main():
    lifespan = Lifespan(parser.parse_args())
    lifespan.main_loop()


if __name__ == "__main__":
    main()
