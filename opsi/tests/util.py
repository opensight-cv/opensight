from unittest.mock import MagicMock, patch

from opsi.lifespan.lifespan import Lifespan
from opsi.manager.program import Program


def create_program():
    lifespan = MagicMock(spec_set=Lifespan)
    program = Program(lifespan)

    return program


def mock_fifolock():
    return patch("opsi.util.concurrency.FifoLock")
