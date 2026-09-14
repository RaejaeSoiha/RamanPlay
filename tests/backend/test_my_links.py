import asyncio
from types import SimpleNamespace

from app.api import routes
from app.services.checker import LinkChecker
from app.watch import links as personal_links
from app.services.personal_links import (
    apply_personal_check,
    best_personal_link,
    reliability_score,
    trust_state,
)
from app.services.security import validate_public_url


class RedirectChecker:
    async def check_personal_details(self, url):
        return "REDIRECT", 302, "https://www.nfl.com/ways-to-watch", 0.1, None, 1


class DirectMediaChecker:
    async def check_personal_details(self, url):
        return "ONLINE", 200, url, 0.1, None, 0


def test_my_links_crud_and_status(client, monkeypatch):
    monkeypatch.setattr(routes, "validate_public_url", lambda url: url)
    monkeypatch.setattr(personal_links, "LinkChecker", RedirectChecker)

    created = client.post(
        "/api/my-links/1",
        json={
            "url": "https://www.nfl.com/watch",
            "source_name": "My NFL link",
            "notes": "Sunday package",
            "priority": 1,
        },
    )
    assert created.status_code == 201
    link = created.json()
    assert link["status"] == "REDIRECT"
    assert link["final_url"] == "https://www.nfl.com/ways-to-watch"
    assert link["successful_check_count"] == 1
    assert link["redirect_count"] == 1
    assert link["trust_state"] == "VERIFIED"

    opened = client.post(f"/api/my-links/{link['id']}/opened")
    assert opened.status_code == 200
    assert opened.json()["last_opened_at"] is not None

    game = client.get("/api/games/1").json()
    assert game["my_links"][0]["id"] == link["id"]

    disabled = client.patch(
        f"/api/my-links/{link['id']}", json={"enabled": False}
    )
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "UNKNOWN"
    assert disabled.json()["final_url"] is None

    edited = client.patch(
        f"/api/my-links/{link['id']}",
        json={"source_name": "Updated link", "priority": 2, "enabled": True},
    )
    assert edited.status_code == 200
    assert edited.json()["source_name"] == "Updated link"
    assert edited.json()["priority"] == 2
    assert edited.json()["status"] == "REDIRECT"

    assert client.delete(f"/api/my-links/{link['id']}").status_code == 204
    assert client.get("/api/my-links/1").json() == []


def test_reliability_tracking_and_best_link_selection():
    def link(id, status="ONLINE", priority=3, successes=0, failures=0, average=0):
        return SimpleNamespace(
            id=id,
            status=status,
            priority=priority,
            enabled=True,
            url="https://www.nfl.com/watch",
            final_url=None,
            final_destination_domain=None,
            last_checked=None,
            last_successful_check=None,
            last_failure=None,
            successful_check_count=successes,
            failure_count=failures,
            average_response_time=average,
            redirect_count=0,
        )

    reliable = link(1, successes=4, average=0.2)
    fallback = link(2, priority=1, successes=1, failures=2, average=2)
    apply_personal_check(
        reliable,
        ("ONLINE", 200, "https://www.nfl.com/watch", 0.4, None, 0),
    )
    apply_personal_check(
        fallback,
        ("OFFLINE", 503, "https://www.nfl.com/watch", 0.1, "Unavailable", 0),
    )

    assert reliable.successful_check_count == 5
    assert reliable.last_successful_check is not None
    assert fallback.failure_count == 3
    assert fallback.last_failure is not None
    assert reliability_score(reliable) > reliability_score(fallback)
    assert best_personal_link([fallback, reliable]) is reliable


def test_personal_link_checker_blocks_denied_redirect(monkeypatch):
    monkeypatch.setattr("app.services.checker.settings.request_interval_seconds", 0)
    monkeypatch.setattr("app.services.checker.settings.blocked_domains", "doubleclick.net")

    def request(url, method):
        if url.endswith("robots.txt"):
            return 404, {}, b""
        if url == "https://www.nfl.com/start":
            return 302, {"location": "https://doubleclick.net/redirect"}, b""
        raise AssertionError("A blocked redirect must not be requested")

    status, _, final_url, _, error, redirects = asyncio.run(
        LinkChecker(request=request).check_personal_details("https://www.nfl.com/start")
    )

    assert (status, final_url, redirects) == (
        "BLOCKED",
        "https://doubleclick.net/redirect",
        1,
    )
    assert error == "Destination domain is blocked"


def test_personal_link_checker_blocks_private_redirect(monkeypatch):
    monkeypatch.setattr("app.services.checker.settings.request_interval_seconds", 0)

    def request(url, method):
        if url.endswith("robots.txt"):
            return 404, {}, b""
        if url == "https://www.nfl.com/start":
            return 302, {"location": "https://127.0.0.1/private"}, b""
        raise AssertionError("A private redirect must not be requested")

    status, _, final_url, _, _, redirects = asyncio.run(
        LinkChecker(request=request).check_personal_details("https://www.nfl.com/start")
    )
    assert (status, final_url, redirects) == ("BLOCKED", "https://127.0.0.1/private", 1)


def test_provider_and_household_actions_require_a_csrf_session(client):
    account = client.get("/api/account/me")
    assert account.status_code == 200
    csrf = account.json()["csrf_token"]

    providers = client.get("/api/provider-accounts")
    assert any(provider["provider"] == "espn" for provider in providers.json())
    connect = client.post(
        "/api/provider-accounts/espn/connect", headers={"X-CSRF-Token": csrf}
    )
    assert connect.json()["mode"] == "official-deep-link"
    assert connect.json()["url"].startswith("https://www.espn.com/")

    invite = client.post(
        "/api/household/invites", headers={"X-CSRF-Token": csrf}, json={}
    )
    assert invite.status_code == 200
    assert invite.json()["code"]
    assert client.post("/api/household/invites", json={}).status_code == 403


def test_manual_public_https_links_are_saveable_and_labeled_unverified(client, monkeypatch):
    monkeypatch.setattr(
        routes, "validate_public_url", lambda url: validate_public_url(url, resolve=False)
    )
    monkeypatch.setattr(personal_links, "LinkChecker", RedirectChecker)
    response = client.post(
        "/api/my-links/1",
        json={
            "url": "https://example.org/watch",
            "source_name": "External link",
        },
    )
    assert response.status_code == 201
    assert response.json()["trust_state"] == "UNVERIFIED"


def test_checked_direct_media_is_classified_for_inline_playback(client, monkeypatch):
    monkeypatch.setattr(routes, "validate_public_url", lambda url: url)
    monkeypatch.setattr(personal_links, "LinkChecker", DirectMediaChecker)
    response = client.post(
        "/api/my-links/1",
        json={
            "url": "https://media.example.test/authorized.m3u8",
            "source_name": "Authorized fixture stream",
            "playback_preference": "AUTO",
        },
    )
    assert response.status_code == 201
    assert response.json()["playback_type"] == "DIRECT_MEDIA"
    assert response.json()["trust_state"] == "UNVERIFIED"


def test_explicit_external_page_stays_external_even_with_a_media_suffix(client, monkeypatch):
    monkeypatch.setattr(routes, "validate_public_url", lambda url: url)
    monkeypatch.setattr(personal_links, "LinkChecker", DirectMediaChecker)
    response = client.post(
        "/api/my-links/1",
        json={
            "url": "https://media.example.test/authorized.m3u8",
            "source_name": "Open externally",
            "playback_preference": "EXTERNAL_PAGE",
        },
    )
    assert response.status_code == 201
    assert response.json()["playback_type"] == "EXTERNAL_PAGE"


def test_my_links_reject_private_unsafe_and_blocked_destinations(client):
    response = client.post(
        "/api/my-links/1",
        json={"url": "https://127.0.0.1/private", "source_name": "Local link"},
    )
    assert response.status_code == 422
    assert "public addresses" in response.json()["detail"]

    unsafe = client.post(
        "/api/my-links/1",
        json={"url": "http://example.org/watch", "source_name": "Unsafe link"},
    )
    assert unsafe.status_code == 422

    malicious = client.post(
        "/api/my-links/1",
        json={"url": "https://doubleclick.net/redirect", "source_name": "Blocked link"},
    )
    assert malicious.status_code == 422
    assert "blocked" in malicious.json()["detail"].lower()


def test_trust_state_distinguishes_verified_unverified_warning_and_blocked():
    link = SimpleNamespace(status="ONLINE", url="https://www.nfl.com/watch")
    assert trust_state(link) == "VERIFIED"
    link.url = "https://example.org/watch"
    assert trust_state(link) == "UNVERIFIED"
    link.status = "WARNING"
    assert trust_state(link) == "WARNING"
    link.status = "BLOCKED"
    assert trust_state(link) == "BLOCKED"


def test_best_link_prefers_checked_direct_media_after_safety():
    external = SimpleNamespace(
        id=1, enabled=True, status="ONLINE", priority=1,
        url="https://example.org/watch", final_url="https://example.org/watch",
        successful_check_count=8, failure_count=0, average_response_time=0.1,
        redirect_count=0,
    )
    direct = SimpleNamespace(
        id=2, enabled=True, status="ONLINE", priority=4,
        url="https://media.example.test/live.m3u8", final_url="https://media.example.test/live.m3u8",
        successful_check_count=1, failure_count=0, average_response_time=0.5,
        redirect_count=0,
    )
    assert best_personal_link([external, direct]) is direct


def test_personal_link_checker_warns_for_unexpected_redirects(monkeypatch):
    monkeypatch.setattr("app.services.checker.settings.request_interval_seconds", 0)

    def request(url, method):
        if url.endswith("robots.txt"):
            return 404, {}, b""
        redirects = {
            "https://www.nfl.com/start": "https://www.nfl.com/step-one",
            "https://www.nfl.com/step-one": "https://www.nfl.com/final",
        }
        if url in redirects:
            return 302, {"location": redirects[url]}, b""
        return 200, {}, b""

    status, _, final_url, _, error = asyncio.run(
        LinkChecker(request=request).check_personal("https://www.nfl.com/start")
    )

    assert status == "WARNING"
    assert final_url == "https://www.nfl.com/final"
    assert error is None


def test_personal_link_checker_stops_after_three_redirects(monkeypatch):
    monkeypatch.setattr("app.services.checker.settings.request_interval_seconds", 0)

    def request(url, method):
        if url.endswith("robots.txt"):
            return 404, {}, b""
        step = int(url.rsplit("/", 1)[-1]) if url.rsplit("/", 1)[-1].isdigit() else 0
        return 302, {"location": f"https://www.nfl.com/{step + 1}"}, b""

    status, _, final_url, _, error = asyncio.run(
        LinkChecker(request=request).check_personal("https://www.nfl.com/0")
    )

    assert status == "WARNING"
    assert final_url == "https://www.nfl.com/3"
    assert error == "Redirect chain exceeded the safe limit"
