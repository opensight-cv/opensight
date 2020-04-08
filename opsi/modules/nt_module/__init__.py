from networktables import NetworkTables

from opsi.util.networking import get_nt_server

from .get import GetNT, HookInstance  # sad
from .put import PutNT

__package__ = "opsi.nt"
__version__ = "0.123"


def init_networktables():
    network = HookInstance.persist.network
    if network.nt_enabled:
        if network.nt_client:
            addr = get_nt_server(network)
            NetworkTables.startClient(addr)
        else:
            NetworkTables.startServer()


def deinit_networktables():
    if HookInstance.persist.network.nt_enabled:
        NetworkTables.shutdown()


HookInstance.add_listener("startup", init_networktables)
HookInstance.add_listener("shutdown", deinit_networktables)
