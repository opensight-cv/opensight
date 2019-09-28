import logging
import os
import subprocess
import tarfile
import tempfile


class UpgradeClient:
    @staticmethod
    def ensure_apt():
        output = subprocess.run(
            "apt -v", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if not output.returncode == 0:
            logging.getLogger(__name__).info("Only Debian derivatives may be upgraded")
            return False
        return True

    def upgrade(self, archive):
        if not UpgradeClient.ensure_apt():
            pass
            # return
        tar = tarfile.open(fileobj=archive.file)
        with tempfile.TemporaryDirectory() as folder:
            tar.extractall(folder)
            command = "apt install" + f" {folder}/".join([""] + os.listdir(folder))
            logging.getLogger(__name__).info("RUNNING UPGRADE COMMAND: " + command)
            # subprocess.run(command, check=True, shell=True)
