import logging
from json import JSONDecodeError
from pathlib import Path

import appdirs
from fastapi import UploadFile
from pydantic import ValidationError

from opsi.webserver.schema import NodeTreeN, Preferences

LOGGER = logging.getLogger(__name__)


class Persistence:
    PATHS = (appdirs.user_data_dir(appname="opensight", appauthor=False),)
    NODETREE_DIR = "nodetrees"
    CALIBRATION_DIR = "calibration"

    instance = None

    def __new__(cls, path=None):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
            cls.instance._is_init = False
        elif path is not None:
            LOGGER.warning(
                f"Attempted to create second instance of singleton {cls} with parameter '{path}'"
            )
        return cls.instance

    def __init__(self, path=None):
        # _is_init is necessary because __init__ is always called after __new__
        if self._is_init:
            return
        self._is_init = True

        self._nodetree = None

        self._prefs = None
        self._profile = None
        self._network = None

        self.paths = self.PATHS
        if path:
            self.paths = (path,)

        self.base_path = self._get_path()

        # handle all preferences here
        self._profile = self.prefs.profile
        self._network = self.prefs.network
        self.nodetree_path = self._get_nt_path()

    def _get_nt_path(self):
        return (
            self.base_path / self.NODETREE_DIR / f"nodetree_{self.profile}.json"
            if self.enabled
            else None
        )

    def _get_path(self):
        for path in self.paths:
            path = Path(path).expanduser().resolve()  # get absolute canonical path

            try:
                LOGGER.debug("Trying path: %s", path)

                # mkdir -p and then ensure file created + write perms
                (path / self.NODETREE_DIR).mkdir(parents=True, exist_ok=True)
                (path / self.CALIBRATION_DIR).mkdir(parents=True, exist_ok=True)
                for i in range(0, 10):
                    (path / self.NODETREE_DIR / f"nodetree_{i}.json").touch()
                (path / "preferences.json").touch()

            except OSError:
                LOGGER.debug("Skipping path %s", path)
                continue

            else:
                LOGGER.info("Decided upon path: %s", path)

                return path

        LOGGER.error("Failed to setup persistence")
        return None

    @property
    def nodetree(self) -> NodeTreeN:
        if self._nodetree:
            return self._nodetree
        try:
            self._nodetree = NodeTreeN.parse_file(self.nodetree_path)
            return self._nodetree
        except (ValidationError, JSONDecodeError, ValueError):
            LOGGER.warning("Unable to parse nodetree persistence")
        except OSError:
            LOGGER.exception("Failed to read from nodetree persistence")

        LOGGER.warning("Creating new NodeTree")
        self._nodetree = NodeTreeN()
        return self._nodetree

    @nodetree.setter
    def nodetree(self, nodetree: NodeTreeN):
        if self.base_path is None:
            return
        self._nodetree = nodetree
        try:
            self.nodetree_path.write_text(nodetree.json())
        except OSError:
            LOGGER.exception("Failed to write to nodetree persistence")

    @property
    def prefs(self) -> Preferences:
        if self._prefs:
            return self._prefs
        try:
            self._prefs = Preferences.parse_file(self.base_path / "preferences.json")
            return self.prefs
        except (ValidationError, JSONDecodeError, ValueError):
            LOGGER.warning("Unable to parse preferences persistence")
        except OSError:
            LOGGER.exception("Failed to read from preferences persistence")

        LOGGER.warning("Creating new preferences")
        self.prefs = Preferences()  # set default preferences in schema.py
        return self._prefs

    @prefs.setter
    def prefs(self, prefs: Preferences):
        if self.base_path is None:
            return
        self._prefs = prefs
        try:
            (self.base_path / "preferences.json").write_text(prefs.json())
        except OSError:
            LOGGER.exception("Failed to write to preferences persistence")

    def update_nodetree(self):
        self._nodetree = None
        self.nodetree_path = self._get_nt_path()
        self.nodetree = self.nodetree  # ensure blank nodetree if not exist

    @property
    def enabled(self):
        return bool(self.base_path)

    @property
    def profile(self):
        return int(self._profile)

    @profile.setter
    def profile(self, value):
        self._profile = value
        self.nodetree_path = self._get_nt_path()
        self.prefs.profile = value
        self.prefs = self.prefs  # write to file
        LOGGER.info(f"Switching to profile {value}")

    @property
    def network(self):
        return self.prefs.network

    @network.setter
    def network(self, value):
        self.nodetree_path = self._get_nt_path()
        self.prefs.network = value
        self.prefs = self.prefs  # write to file

    def add_calibration_file(self, file: UploadFile):
        if self.base_path is None:
            return
        try:
            (self.base_path / self.CALIBRATION_DIR / file.filename).write_bytes(
                file.file.read()
            )
        except OSError:
            LOGGER.exception("Failed to write to preferences persistence")

    def get_all_calibration_files(self):
        return list((self.base_path / self.CALIBRATION_DIR).glob("*.yaml"))

    def get_calibration_file_path(self, name):
        try:
            return self.base_path / self.CALIBRATION_DIR / name
        except OSError:
            LOGGER.exception("Failed to read calibration file")


class NullPersistence(Persistence):
    # Disable saving anything to disk
    # Should not cause errors outside this file

    def _get_path(self):
        LOGGER.debug("Null persistence")
        return Path("/dev/null")
