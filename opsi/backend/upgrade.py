import logging
import subprocess
import tarfile
import tempfile

from opsi.util.path import join

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
        LOGGER.info("Only Debian derivatives may be upgraded", exc_info=True)
        return False
    return True


def upgrade_opsi(archive, lifespan):
    if not ensure_apt():
        return

    path = join(__file__, "upgrade.sh")

    with tempfile.TemporaryDirectory(prefix="opensight_upgrade.") as tempdir:
        try:
            with tarfile.open(fileobj=archive.file) as tar:
                tar.extractall(tempdir)
        except tarfile.ReadError:
            LOGGER.info("File provided is not a tar file", exc_info=True)
            return

        command = f"{path} {tempdir}"
        subprocess.Popen(command, shell=True)

    lifespan.shutdown()
