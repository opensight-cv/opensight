import logging

from opsi.util.path import join

# silence fastapi warning about email-validator
logging.getLogger("fastapi").setLevel(logging.ERROR)

# silence mutlipart excessive debug output
logging.getLogger("multipart").setLevel(logging.ERROR)

__version__ = "master"

try:
    with open(join(__file__, "version.py")) as f:
        __version__ = f.read().strip()
except OSError:
    pass
