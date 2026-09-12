import asyncio
import socket
import ssl
import time
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import certifi
from sqlalchemy import select

from app.config import settings
from app.models.entities import (
    Game,
    LinkCheck,
    MaintenanceState,
    PersonalLink,
    WatchSource,
    now,
)
from app.services.security import validate_url


# Connect to an already validated public address, retaining TLS SNI and Host.
# This prevents DNS rebinding between validation and the outbound connection.
def pinned_request(url, method):
    validate_url(url, resolve=False)
    p = urlsplit(url)
    host = p.hostname
    import ipaddress

    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not addresses or any(
        not ipaddress.ip_address(a[4][0]).is_global for a in addresses
    ):
        raise ValueError("Non-public address")
    import http.client

    connection = http.client.HTTPSConnection(
        host, timeout=10, context=ssl.create_default_context(cafile=certifi.where())
    )
    address = addresses[0]
    raw = socket.socket(address[0], address[1], address[2])
    raw.settimeout(10)
    try:
        raw.connect(address[4])
        connection.sock = connection._context.wrap_socket(raw, server_hostname=host)
        path = p.path or "/"
        if p.query:
            path += "?" + p.query
        connection.request(
            method,
            path,
            headers={
                "Host": host,
                "User-Agent": settings.user_agent,
                "Range": "bytes=0-65535",
            }
            if method == "GET"
            else {"Host": host, "User-Agent": settings.user_agent},
        )
        response = connection.getresponse()
        return (
            response.status,
            dict((k.lower(), v) for k, v in response.getheaders()),
            response.read(65536) if method == "GET" else b"",
        )
    finally:
        connection.close()
        raw.close()


class LinkChecker:
    def __init__(self, request=pinned_request):
        self.request = request
        self.robots = {}
        self.results = {}

    async def fetch(self, url, method):
        result = None
        for attempt in range(3):
            await asyncio.sleep(
                max(settings.request_interval_seconds, 0.01) * (2**attempt)
            )
            try:
                result = await asyncio.to_thread(self.request, url, method)
            except (OSError, TimeoutError):
                if attempt == 2:
                    raise
                continue
            if result[0] not in (429, 500, 502, 503, 504):
                break
        return result

    async def allowed(self, url):
        p = urlsplit(url)
        origin = f"https://{p.netloc}"
        if origin not in self.robots:
            code, _, body = await self.fetch(origin + "/robots.txt", "GET")
            parser = RobotFileParser()
            if code in (404, 410):
                self.robots[origin] = True
            elif code == 200:
                parser.parse(body.decode("utf8", errors="replace").splitlines())
                self.robots[origin] = parser
            else:
                self.robots[origin] = False
        rule = self.robots[origin]
        if isinstance(rule, bool):
            return rule
        delay = rule.crawl_delay(settings.user_agent) or 0
        if delay:
            await asyncio.sleep(min(delay, 60))
        return rule.can_fetch(settings.user_agent, url) and delay <= 60

    async def check(self, url):
        return (await self._check(url, max_redirects=5, warn_on_suspicious_redirects=False))[:5]

    async def check_personal(self, url):
        """Check a My Link with a short redirect limit and conservative warnings."""
        return (await self.check_personal_details(url))[:5]

    async def check_personal_details(self, url):
        return await self._check(url, max_redirects=3, warn_on_suspicious_redirects=True)

    async def _check(self, url, max_redirects, warn_on_suspicious_redirects):
        started = time.monotonic()
        current = url
        code = None
        redirect = 0
        try:
            for redirect in range(max_redirects + 1):
                if self._is_denied(current):
                    return (
                        "BLOCKED",
                        None,
                        current,
                        time.monotonic() - started,
                        "Destination domain is blocked",
                        redirect,
                    )
                validate_url(current, resolve=False)
                if not await self.allowed(current):
                    return (
                        "BLOCKED",
                        None,
                        current,
                        time.monotonic() - started,
                        "robots.txt disallows or could not be verified",
                        redirect,
                    )
                code, headers, _ = await self.fetch(current, "HEAD")
                if code in (405, 501):
                    code, headers, _ = await self.fetch(current, "GET")
                if code in (301, 302, 303, 307, 308):
                    if "location" not in headers:
                        raise ValueError("Missing redirect location")
                    if redirect == max_redirects:
                        if warn_on_suspicious_redirects:
                            return (
                                "WARNING",
                                code,
                                current,
                                time.monotonic() - started,
                                "Redirect chain exceeded the safe limit",
                                redirect + 1,
                            )
                        raise ValueError("Too many redirects")
                    current = urljoin(current, headers["location"])
                    continue
                state = (
                    "REDIRECT"
                    if redirect and 200 <= code < 300
                    else "ONLINE"
                    if 200 <= code < 300
                    else "NOT_FOUND"
                    if code in (404, 410)
                    else "BLOCKED"
                    if code in (401, 403, 429)
                    else "ERROR"
                )
                if warn_on_suspicious_redirects and redirect and (
                    redirect > 1 or self._site(url) != self._site(current)
                ):
                    state = "WARNING"
                return state, code, current, time.monotonic() - started, None, redirect
        except Exception as exc:
            return (
                "ERROR",
                code,
                current,
                time.monotonic() - started,
                f"Request failed or destination rejected ({type(exc).__name__})",
                redirect,
            )

    @staticmethod
    def _site(url):
        host = (urlsplit(url).hostname or "").lower().rstrip(".")
        parts = host.split(".")
        return ".".join(parts[-2:]) if len(parts) >= 2 else host

    @staticmethod
    def _is_denied(url):
        host = (urlsplit(url).hostname or "").lower().rstrip(".")
        return any(
            host == domain or host.endswith("." + domain)
            for domain in (item.strip().lower() for item in settings.blocked_domains.split(","))
            if domain
        )

    async def check_all(self, db):
        sources = list(db.scalars(select(WatchSource)))
        personal_links = list(
            db.scalars(select(PersonalLink).where(PersonalLink.enabled))
        )
        for s in sources:
            if s.url not in self.results:
                self.results[s.url] = await self.check(s.url)
            status, code, final, elapsed, error = self.results[s.url]
            s.status = status
            s.last_checked = now()
            s.final_url = final
            db.add(
                LinkCheck(
                    watch_source_id=s.id,
                    http_status=code,
                    response_time=elapsed,
                    is_available=status in ("ONLINE", "REDIRECT"),
                    error_message=error,
                    final_url=final,
                )
            )
        for link in personal_links:
            cache_key = ("personal", link.url)
            if cache_key not in self.results:
                self.results[cache_key] = await self.check_personal_details(link.url)
            from app.services.personal_links import apply_personal_check

            apply_personal_check(link, self.results[cache_key])
        db.merge(MaintenanceState(key="last_link_check", value=now().isoformat()))
        db.commit()
        return len(sources) + len(personal_links)

    async def check_near_kickoff_links(self, db, current):
        from datetime import timedelta
        from app.services.personal_links import apply_personal_check

        links = list(
            db.scalars(
                select(PersonalLink)
                .join(Game, PersonalLink.game_id == Game.id)
                .where(
                    PersonalLink.enabled,
                    Game.kickoff_time >= current,
                    Game.kickoff_time <= current + timedelta(minutes=15),
                )
            )
        )
        for link in links:
            checked_at = link.last_checked
            if checked_at and checked_at.tzinfo is None:
                checked_at = checked_at.replace(tzinfo=current.tzinfo)
            if not checked_at or (current - checked_at).total_seconds() >= 300:
                apply_personal_check(link, await self.check_personal_details(link.url))
        db.commit()
        return len(links)
