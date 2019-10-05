#!/usr/bin/env python3
import logging
import threading
import time

from opsi.lifespan.lifespan import Lifespan

logging.basicConfig(level=logging.ERROR)
LOGGER = logging.getLogger(__name__)


def main():
    lifespan = Lifespan()
    lifespan.main_loop()


if __name__ == "__main__":
    main()
