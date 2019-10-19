import logging
import socket

import netifaces

LOGGER = logging.getLogger(__name__)


def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            LOGGER.debug(f"Couldn't bind to port {port}", exc_info=True)
            return False


def get_server_url(network, port=80, prefix="/"):
    assert prefix.endswith("/")

    port_str = "" if port == 80 else f":{port}"

    teamStr = f"{network['team']:04d}"

    # default to mdns in case static fails for some reason
    hostname = f"{socket.gethostname()}.local"
    if network["static"]:
        host_prefix = f"10.{teamStr[:2]}.{teamStr[2:]}"
        # TODO: Make work for more than eth0
        # also todo cleanup
        for i in netifaces.ifaddresses("eth0").values():
            for x in i:
                if host_prefix in str(x.get("addr")):
                    hostname = x.get("addr")

    return f"http://{hostname}{port_str}{prefix}"


def get_roborio_url(network):
    teamStr = f"{network['team']:04d}"
    if network["static"]:
        hostname = f"10.{teamStr[:2]}.{teamStr[2:]}.2"
    else:
        hostname = f"roboRIO-{teamStr}-FRC.local"
    return hostname


def choose_port(ports):
    if isinstance(ports, int):
        ports = (ports,)

    for port in ports:
        if is_port_open(port):
            return port

    return None
