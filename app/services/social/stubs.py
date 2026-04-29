"""Stubbed posters for platforms that need significant per-platform setup.

These return a "not implemented" result so the rest of the system stays clean.
When you're ready to implement one, swap the stub for a real implementation
following the same pattern as linkedin.py.
"""
from app.services.social.base import EventPost, PostResult


class TwitterPoster:
    """Twitter/X posting.

    Requirements:
    - Twitter API access (Basic tier is paid as of 2024, ~$100/month)
    - Developer app at https://developer.twitter.com
    - OAuth 2.0 user context auth (most complex of all the platforms here)

    Implementation notes when you're ready:
    - Endpoint: POST https://api.twitter.com/2/tweets
    - Body: {"text": "..."}
    - Note: 280 character limit; auto-truncate description before sending.
    """
    name = "Twitter/X"

    def is_configured(self) -> bool:
        return False

    async def post(self, event: EventPost) -> PostResult:
        return PostResult(
            platform=self.name,
            success=False,
            message="Not implemented. Requires paid Twitter API access.",
        )


class FacebookPoster:
    """Facebook Page posting.

    Requirements:
    - Facebook Page (not a personal profile)
    - Facebook Developer app at https://developers.facebook.com
    - App review for `pages_manage_posts` permission (takes 1-2 weeks)
    - Page Access Token (long-lived)

    Implementation notes when you're ready:
    - Endpoint: POST https://graph.facebook.com/v19.0/{page-id}/feed
    - Body: {"message": "...", "link": "...", "access_token": "..."}
    """
    name = "Facebook"

    def is_configured(self) -> bool:
        return False

    async def post(self, event: EventPost) -> PostResult:
        return PostResult(
            platform=self.name,
            success=False,
            message="Not implemented. Requires Facebook app review.",
        )


class InstagramPoster:
    """Instagram posting.

    Requirements:
    - Instagram Business or Creator account (linked to a Facebook Page)
    - Same Facebook Developer app as above with Instagram Graph API enabled
    - Instagram requires an IMAGE OR VIDEO — text-only posts not supported

    Implementation notes when you're ready:
    - Two-step: create container, then publish.
    - You'll need to generate or upload a graphic for each event.
    """
    name = "Instagram"

    def is_configured(self) -> bool:
        return False

    async def post(self, event: EventPost) -> PostResult:
        return PostResult(
            platform=self.name,
            success=False,
            message="Not implemented. Requires images and Facebook Business setup.",
        )
