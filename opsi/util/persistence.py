import json
import logging
from os import makedirs
from os.path import expanduser, join


class PersistentNodetree:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.nodetree = None
        self.path = self.__get_path__()

    def __get_path__(self):
        return self.__create__("/var/lib/opensight") or self.__create__(
            join(expanduser("~"), ".local/share/opensight")
        )
        self.logger.error("Failed to setup nodetree persistent")
        return None

    def __create__(self, path):
        try:
            # mkdir -p and then ensure file created + write perms
            makedirs(path, exist_ok=True)
            open(join(path, "nodetree.json"), "a+").close()
        except IOError as e:
            self.logger.debug(e, exc_info=True)
            return None
        return path

    def set(self, nodetree):
        if self.path is None:
            return
        self.nodetree = nodetree
        try:
            with open(join(self.path, "nodetree.json"), "w") as file:
                file.write(nodetree.json())
        except Exception as e:
            self.logger.exception(e)
            self.logger.error("Failed to write to nodetree persistence")

    def get(self):
        if self.nodetree:
            return self.nodetree
        try:
            with open(join(self.path, "nodetree.json"), "r") as file:
                return json.load(file)
        except json.decoder.JSONDecodeError:
            self.logger.info("Nodetree persistence invalid, continuing...")
        except Exception as e:
            self.logger.exception(e)
            self.logger.error("Failed to read from nodetree persistence")
        return None
