import logging
import os
import subprocess
import tarfile
import tempfile

LOGGER = logging.getLogger(__name__)


def ensure_apt():
    try:
        subprocess.run(
            "apt -v",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        LOGGER.info("Only Debian derivatives may be upgraded")
        return False
    return True


def upgrade_opsi(archive):
    if not ensure_apt():
        return
    try:
        tar = tarfile.open(fileobj=archive.file)
        with tempfile.TemporaryDirectory() as folder:
            tar.extractall(folder)
            command = f"dpkg -Ri {folder}"
            LOGGER.debug("RUNNING UPGRADE COMMAND: %s", command)
            subprocess.run(command, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        LOGGER.error("Failed to upgrade from uploaded tarfile")
        LOGGER.debug(e, exc_info=True)
