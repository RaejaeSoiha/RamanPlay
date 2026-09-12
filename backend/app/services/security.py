import ipaddress, socket
from urllib.parse import urlsplit
from app.config import settings


def validate_url(url: str, resolve: bool = True):
    p = urlsplit(url)
    host = (p.hostname or "").lower()
    allowed = settings.trusted_domains.split(",")
    if (
        p.scheme != "https"
        or p.username
        or p.password
        or p.port not in (None, 443)
        or not any(
            host == d.strip() or host.endswith("." + d.strip())
            for d in allowed
            if d.strip()
        )
    ):
        raise ValueError("Only HTTPS URLs on approved domains are permitted")
    if resolve:
        addresses = {
            row[4][0] for row in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        }
        if not addresses or any(
            not ipaddress.ip_address(a).is_global for a in addresses
        ):
            raise ValueError("Destination must resolve exclusively to public addresses")
    return url
