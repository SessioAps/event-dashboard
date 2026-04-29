"""Dispatcher: posts a single event to all configured social platforms in parallel."""
import asyncio
import logging

from app.services.social.base import EventPost, PostResult, SocialPoster
from app.services.social.linkedin import LinkedInPoster
from app.services.social.stubs import FacebookPoster, InstagramPoster, TwitterPoster

logger = logging.getLogger(__name__)


def get_all_posters() -> list[SocialPoster]:
    """Return one instance of every poster. Order = display order in the UI."""
    return [LinkedInPoster(), TwitterPoster(), FacebookPoster(), InstagramPoster()]


def get_configured_posters() -> list[SocialPoster]:
    return [p for p in get_all_posters() if p.is_configured()]


async def post_to_all(event: EventPost) -> list[PostResult]:
    """Post an event to every configured platform, in parallel."""
    posters = get_configured_posters()
    if not posters:
        return []

    results = await asyncio.gather(
        *(p.post(event) for p in posters), return_exceptions=True
    )

    final: list[PostResult] = []
    for poster, result in zip(posters, results):
        if isinstance(result, Exception):
            logger.exception("Poster %s raised", poster.name)
            final.append(
                PostResult(platform=poster.name, success=False, message=f"Crashed: {result}")
            )
        else:
            final.append(result)
    return final
