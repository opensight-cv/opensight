import logging
from json import JSONDecodeError
from pathlib import PosixPath

from pydantic import ValidationError

from ..webserver.schema import NodeTreeN

logger = logging.getLogger(__name__)


class PersistentNodetree:
    PATHS = ("/var/lib/opensight", "~/.local/share/opensight")
    NODETREE_PATH = "nodetree.json"

    def __init__(self):
        self._nodetree = None

        self.base_path = self._get_path()
        self.nodetree_path = (
            self.base_path / self.NODETREE_PATH if self.enabled else None
        )

    def _get_path(self):
        for path in self.PATHS:
            path = PosixPath(path).expanduser().resolve()  # get absolute canonical path

            try:
                logger.debug("Trying path: %s", path)

                # mkdir -p and then ensure file created + write perms
                path.mkdir(parents=True, exist_ok=True)
                (path / self.NODETREE_PATH).touch()

            except OSError:
                logger.debug("Skipping path", exc_info=True)
                continue

            else:
                logger.info("Decided upon path: %s", path)

                return path

        logger.error("Failed to setup persistence")
        return None

    @property
    def nodetree(self) -> NodeTreeN:
        if self._nodetree:
            return self._nodetree

        try:
            self._nodetree = NodeTreeN.parse_file(self.nodetree_path)
            return self._nodetree
        except (ValidationError, JSONDecodeError):
            logger.warning("Nodetree persistence invalid", exc_info=True)
        except OSError:
            logger.exception("Failed to read from nodetree persistence")

        return None

    @nodetree.setter
    def nodetree(self, nodetree: NodeTreeN):
        if self.base_path is None:
            return

        self._nodetree = nodetree

        try:
            self.nodetree_path.write_text(nodetree.json())
        except OSError:
            logger.exception("Failed to write to nodetree persistence")

    @property
    def enabled(self):
        return bool(self.base_path)
