import logging
import socket

LOGGER = logging.getLogger(__name__)


def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            LOGGER.debug(f"Couldn't bind to port {port}", exc_info=True)
            return False


def get_server_url(port=80, prefix="/"):
    assert prefix.endswith("/")

    port_str = "" if port == 80 else f":{port}"
    hostname = socket.gethostname()

    return f"http://{hostname}.local{port_str}{prefix}"


def choose_port(ports):
    if isinstance(ports, int):
        ports = (ports,)

    for port in ports:
        if is_port_open(port):
            return port

    return None
