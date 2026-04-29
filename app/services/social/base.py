"""Social media auto-posting.

Architecture: each platform implements a `SocialPoster` with a `post()` method.
The dispatcher in `__init__.py` calls all configured posters in parallel and
aggregates results.

Currently implemented:
- LinkedIn (working, requires developer app setup)

Stubbed (TODO):
- Twitter/X — requires paid API access ($100/mo basic tier as of 2024)
- Facebook Page — requires app review for posting permissions
- Instagram — requires Business account + Facebook Graph API
"""
from dataclasses import dataclass
from typing import Protocol


@dataclass
class PostResult:
    platform: str
    success: bool
    message: str
    url: str | None = None


@dataclass
class EventPost:
    """The content we want to publish to social media."""
    title: str
    description: str
    location: str | None
    start_at_iso: str  # human-readable date string
    public_url: str   # link to the event page on our site


class SocialPoster(Protocol):
    name: str

    async def post(self, event: EventPost) -> PostResult:
        ...

    def is_configured(self) -> bool:
        ...
