import logging
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
        LOGGER.info(
            "Only Debian derivatives may be upgraded. If you are using a Debian derivative and receiving this error, please make a bug report.",
            exc_info=True,
        )
        return False
    return True


def upgrade_opsi(archive, lifespan):
    if not ensure_apt():
        return

    tempdir = tempfile.mkdtemp()
    try:
        with tarfile.open(fileobj=archive.file) as tar:
            tar.extractall(tempdir)
    except tarfile.ReadError:
        LOGGER.info("File provided is not a tar file", exc_info=True)
        return
    command = f"{tempdir}/upgrade.sh"
    subprocess.Popen(command, cwd=tempdir)
    lifespan.shutdown()
