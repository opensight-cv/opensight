import pytest

from .util import mock_fifolock  # noqa
from .util import create_program


def test_invalid_function_type_causes_error():
    from opsi.webserver.schema import NodeN, NodeTreeN
    from opsi.webserver.serialize import NodeTreeImportError, import_nodetree

    program = create_program()

    assert not program.pipeline.broken

    node = NodeN(type="nonexistent", id="1")
    nodetree = NodeTreeN(nodes=[node])

    with pytest.raises(NodeTreeImportError) as excinfo:
        import_nodetree(program, nodetree)

    error: NodeTreeImportError = excinfo.value
    assert error.node == node

    assert program.pipeline.broken
