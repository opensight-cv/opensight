from typing import Optional


def set_network_mode(dhcp: bool, team_number: Optional[int], static_ip_extension: Optional[int]):
    if dhcp:
        with open('templates/dhcp.conf', 'r') as template:
            data = template.read()
            with open("/etc/dhcpcd.conf", "w") as output:
                output.write(data)
    else:
        # 4 digit team number with leading zeros
        team_padded = f"{team_number:04d}"
        router_ip = f"10.{team_padded[0:2]}.{team_padded[2:4]}.1"
        static_ip = f"10.{team_padded[0:2]}.{team_padded[2:4]}.{static_ip_extension}"
        with open('templates/static.conf', 'r') as template:
            data = template.read()
            data = data.replace("STATIC_IP_ADDR", static_ip).replace("ROUTER_IP_ADDR", router_ip)
            with open("/etc/dhcpcd.conf", "w") as output:
                output.write(data)

    # TODO: reboot
