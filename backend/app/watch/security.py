import ipaddress, socket
from urllib.parse import urlsplit
from app.config import settings


def _domains(value: str):
    return tuple(item.strip().lower().rstrip(".") for item in value.split(",") if item.strip())


def is_trusted_domain(host: str) -> bool:
    host = host.lower().rstrip(".")
    return any(host == domain or host.endswith("." + domain) for domain in _domains(settings.trusted_domains))


def is_blocked_domain(host: str) -> bool:
    host = host.lower().rstrip(".")
    return any(host == domain or host.endswith("." + domain) for domain in _domains(settings.blocked_domains))


def validate_public_url(url: str, resolve: bool = True):
    p = urlsplit(url)
    host = (p.hostname or "").lower()
    try:
        port = p.port
    except ValueError as exc:
        raise ValueError("Use a valid HTTPS URL without embedded credentials") from exc
    if (
        p.scheme != "https"
        or not p.netloc
        or not host
        or p.username
        or p.password
        or port not in (None, 443)
    ):
        raise ValueError("Use a valid HTTPS URL without embedded credentials")
    if host == "localhost" or host.endswith(".localhost") or is_blocked_domain(host):
        raise ValueError("This destination is blocked")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address and not address.is_global:
        raise ValueError("Destination must resolve exclusively to public addresses")
    if resolve:
        try:
            addresses = {
                row[4][0] for row in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            }
        except OSError as exc:
            raise ValueError("Destination could not be resolved") from exc
        if not addresses or any(
            not ipaddress.ip_address(a).is_global for a in addresses
        ):
            raise ValueError("Destination must resolve exclusively to public addresses")
    return url


def validate_url(url: str, resolve: bool = True):
    """Validate a trusted provider URL used by official source integrations."""
    validated = validate_public_url(url, resolve)
    if not is_trusted_domain((urlsplit(validated).hostname or "").lower()):
        raise ValueError("Only HTTPS URLs on approved domains are permitted")
    return validated
