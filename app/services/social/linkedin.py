"""LinkedIn auto-posting.

Setup (one-time):

1. Go to https://www.linkedin.com/developers/apps and create a new app.
   - You need a LinkedIn Page for your company to associate it with.

2. In the app's "Products" tab, request access to:
   - "Share on LinkedIn"
   - "Sign In with LinkedIn using OpenID Connect"
   - "Marketing Developer Platform" (only if you want to post AS the company
     page rather than as yourself)

3. Generate an access token:
   - For posting as yourself: use the Auth tab → "OAuth 2.0 tools" →
     "Generate token" → request scope `w_member_social`.
   - For posting as a company page: scope `w_organization_social` and you
     also need the page's organization URN (looks like `urn:li:organization:12345`).
     You can find it via the API: GET /v2/organizationAcls?q=roleAssignee

4. Add to .env:
   LINKEDIN_ACCESS_TOKEN=your-token-here
   LINKEDIN_ORGANIZATION_URN=urn:li:organization:12345    (only if posting as company)

Note: LinkedIn access tokens expire (typically 60 days for member tokens).
For a real production setup you'd implement the full OAuth refresh flow.
For getting started, regenerate manually when needed.
"""
import logging

import httpx

from app.config import settings
from app.services.social.base import EventPost, PostResult

logger = logging.getLogger(__name__)


class LinkedInPoster:
    name = "LinkedIn"

    def is_configured(self) -> bool:
        return bool(settings.linkedin_access_token)

    async def post(self, event: EventPost) -> PostResult:
        if not self.is_configured():
            return PostResult(
                platform=self.name,
                success=False,
                message="LinkedIn not configured (missing LINKEDIN_ACCESS_TOKEN)",
            )

        # Build the post text. LinkedIn allows up to 3000 characters.
        text = self._build_text(event)

        # If an organization URN is set, post as the company page.
        # Otherwise post as the authenticated member.
        author = settings.linkedin_organization_urn or await self._get_member_urn()
        if not author:
            return PostResult(
                platform=self.name,
                success=False,
                message="Could not determine LinkedIn author URN",
            )

        payload = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "ARTICLE",
                    "media": [
                        {
                            "status": "READY",
                            "originalUrl": event.public_url,
                            "title": {"text": event.title},
                            "description": {"text": event.description[:200] if event.description else ""},
                        }
                    ],
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.linkedin.com/v2/ugcPosts",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.linkedin_access_token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
            )

        if response.status_code >= 400:
            logger.error("LinkedIn post failed %s: %s", response.status_code, response.text)
            return PostResult(
                platform=self.name,
                success=False,
                message=f"API error {response.status_code}: {response.text[:200]}",
            )

        post_id = response.headers.get("x-restli-id") or response.json().get("id", "")
        return PostResult(
            platform=self.name,
            success=True,
            message="Posted successfully",
            url=f"https://www.linkedin.com/feed/update/{post_id}/" if post_id else None,
        )

    def _build_text(self, event: EventPost) -> str:
        parts = [f"📅 {event.title}", "", f"🗓 {event.start_at_iso}"]
        if event.location:
            parts.append(f"📍 {event.location}")
        if event.description:
            parts.append("")
            parts.append(event.description[:500])
        parts.append("")
        parts.append(f"More info: {event.public_url}")
        return "\n".join(parts)

    async def _get_member_urn(self) -> str | None:
        """Fetch the authenticated member's URN. Used when posting as a person."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {settings.linkedin_access_token}"},
            )
        if response.status_code >= 400:
            logger.error("Failed to fetch LinkedIn user info: %s", response.text)
            return None
        sub = response.json().get("sub")
        return f"urn:li:person:{sub}" if sub else None
