from datetime import datetime, timezone
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from app.models.entities import PersonalLink
from app.services.checker import LinkChecker


def serialize_personal_link(link: PersonalLink) -> dict:
    result = {
        column.name: getattr(link, column.name) for column in link.__table__.columns
    }
    result["reliability_score"] = reliability_score(link)
    return result


def reliability_score(link: PersonalLink) -> int:
    checks = link.successful_check_count + link.failure_count
    if not checks:
        return 0
    success_rate = link.successful_check_count / checks
    speed_score = max(0, 20 - min(link.average_response_time, 5) * 4)
    redirect_penalty = min(10, link.redirect_count * 2)
    return round(max(0, success_rate * 80 + speed_score - redirect_penalty))


def best_personal_link(links: list[PersonalLink]) -> PersonalLink | None:
    enabled = [link for link in links if link.enabled]
    if not enabled:
        return None
    status_rank = {"ONLINE": 0, "REDIRECT": 1, "WARNING": 2, "UNKNOWN": 3, "OFFLINE": 4, "BLOCKED": 5}
    return min(
        enabled,
        key=lambda link: (
            status_rank.get(link.status, 6),
            -reliability_score(link),
            link.priority,
            link.id,
        ),
    )


def serialize_personal_links(links: list[PersonalLink]) -> list[dict]:
    best = best_personal_link(links)
    return [
        {
            **serialize_personal_link(link),
            "is_best": best is not None and link.id == best.id,
        }
        for link in sorted(
            links,
            key=lambda link: (
                0 if link.status == "ONLINE" and link.enabled else 1,
                -reliability_score(link),
                link.priority,
                link.id,
            ),
        )
    ]


def apply_personal_check(
    link: PersonalLink,
    result: tuple[str, int | None, str | None, float, str | None, int],
) -> None:
    status, _, final_url, elapsed, error, redirects = result
    checked_at = datetime.now(timezone.utc)
    link.status = status if status in {"ONLINE", "REDIRECT", "WARNING", "BLOCKED"} else "OFFLINE"
    link.final_url = None if status == "WARNING" and error else final_url
    link.final_destination_domain = (
        (urlsplit(final_url).hostname or "").lower() if link.final_url else None
    )
    link.last_checked = checked_at
    link.redirect_count = redirects
    if status in {"ONLINE", "REDIRECT"}:
        previous = link.successful_check_count
        link.successful_check_count = previous + 1
        link.average_response_time = (
            (link.average_response_time * previous + elapsed) / (previous + 1)
        )
        link.last_successful_check = checked_at
    else:
        link.failure_count += 1
        link.last_failure = checked_at


async def check_personal_link(db: Session, link: PersonalLink) -> PersonalLink:
    if not link.enabled:
        link.status = "UNKNOWN"
        link.final_url = None
        link.last_checked = None
        db.commit()
        db.refresh(link)
        return link

    result = await LinkChecker().check_personal_details(link.url)
    apply_personal_check(link, result)
    db.commit()
    db.refresh(link)
    return link
