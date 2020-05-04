from unittest.mock import MagicMock, patch

import pytest

from opsi.webserver.schema import NodeN, NodeTreeN
from opsi.webserver.serialize import NodeTreeImportError, import_nodetree

from .util import create_program, mock_fifolock


def test_invalid_function():
    program = create_program()

    node = NodeN(type="nonexistent", id="1")
    nodetree = NodeTreeN(nodes=[node])

    with mock_fifolock(), pytest.raises(NodeTreeImportError) as excinfo:
        import_nodetree(program, nodetree)

    error: NodeTreeImportError = excinfo.value
    assert error.node == node
