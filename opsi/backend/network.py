import os
from pathlib import Path


def set_network_mode(
    dhcp: bool, team_number: int, static_ip_extension: int, lifespan: "Lifespan",
):
    template_dir = Path(os.path.dirname(__file__), "templates")
    if dhcp:
        with open(template_dir / "dhcp.conf", "r") as template:
            data = template.read()
            with open("/etc/dhcpcd.conf", "w") as output:
                output.write(data)
    else:
        # 4 digit team number with leading zeros
        team_padded = f"{team_number:04d}"
        router_ip = f"10.{team_padded[0:2]}.{team_padded[2:4]}.1"
        static_ip = f"10.{team_padded[0:2]}.{team_padded[2:4]}.{static_ip_extension}"
        with open(template_dir / "static.conf", "r") as template:
            data = template.read()
            data = data.replace("STATIC_IP_ADDR", static_ip).replace(
                "ROUTER_IP_ADDR", router_ip
            )
            with open("/etc/dhcpcd.conf", "w") as output:
                output.write(data)

    lifespan.restart(host=True)


def dhcpcd_writable():
    path = "/etc/dhcpcd.conf"
    if os.path.exists(path) and os.path.isfile(path):
        return os.access(path, os.W_OK)
