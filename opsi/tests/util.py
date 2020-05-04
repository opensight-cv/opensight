from unittest.mock import MagicMock, patch

import pytest


def create_program():
    from opsi.lifespan.lifespan import Lifespan
    from opsi.manager.program import Program

    lifespan = MagicMock(spec_set=Lifespan)
    program = Program(lifespan)

    return program


# If mock_fifolock is imported in a test.py,
# then every test in it will be run with this mock applied
@pytest.fixture(autouse=True)
def mock_fifolock():
    with patch("opsi.util.concurrency.FifoLock", autospec=True, spec_set=True):
        yield
