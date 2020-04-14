import logging
from pathlib import Path

# silence fastapi warning about email-validator
logging.getLogger("fastapi").setLevel(logging.ERROR)

# silence mutlipart excessive debug output
logging.getLogger("multipart").setLevel(logging.ERROR)

__version__ = None

try:
    with open(Path(__file__) / "version.py") as f:
        __version__ = f.read().strip()
except OSError:
    pass

if not __version__:
    try:
        with open(Path(__file__).parent.parent / ".git/HEAD") as f:
            __version__ = "/".join(f.read().split("/")[2:]).strip()
    except (OSError, IndexError) as e:
        pass

if not __version__:
    __version__ = "unknown"
