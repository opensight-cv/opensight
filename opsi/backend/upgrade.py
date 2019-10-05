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


def upgrade_opsi(archive, lifespan):
    if not ensure_apt():
        return
    tempdir = tempfile.mkdtemp()
    path = os.path.join(os.path.dirname(__file__), "upgrade.sh")
    try:
        tar = tarfile.open(fileobj=archive.file)
    except tarfile.ReadError:
        LOGGER.info("File provided is not a tar file")
        return
    tar.extractall(tempdir)
    command = f"{path} {tempdir}"
    subprocess.Popen(command, shell=True)
    lifespan.shutdown()
