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


def get_static_hostname(prefix=""):
    for interface in netifaces.interfaces():
        # Get list of ipv4 addresses of this interface
        addr_list = netifaces.ifaddresses(interface).get(netifaces.AF_INET, ())

        for addr_dict in addr_list:
            addr = addr_dict.get("addr")
            if addr is not None and addr.startswith(prefix):
                return addr


def get_server_url(lifespan, port=80, prefix="/"):
    network = lifespan.persist.network
    assert prefix.endswith("/")

    port_str = "" if port == 80 else f":{port}"

    # default to mdns in case static fails for some reason
    teamStr = network.team
    hostname = f"{socket.gethostname()}.local"

    if network.static:
        host_prefix = f"10.{teamStr[:2]}.{teamStr[2:]}"
        static = get_static_hostname(host_prefix)
        hostname = static if static else hostname  # ensure static isn't None

    if network.nt_enabled and not network.nt_client:
        if lifespan.using_systemd:
            hostname = "opensight.local"
        else:
            hostname = "localhost"

    return f"http://{hostname}{port_str}{prefix}"


def get_nt_server(network):
    teamStr = network.team

    if network.static:
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
