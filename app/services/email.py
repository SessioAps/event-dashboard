"""Email sending via Resend.

Resend is recommended because it has the simplest setup of any modern email
provider: sign up, verify your domain (or use their sandbox), grab an API key,
done. Free tier is 3,000 emails/month, 100/day.

To use:
1. Sign up at https://resend.com
2. Create an API key in the dashboard
3. Add to .env:    RESEND_API_KEY=re_...
4. (Optional) Add a verified sending domain. Until then, use the sandbox
   address `onboarding@resend.dev` as the FROM address.
"""
import logging
from typing import Iterable

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class EmailError(Exception):
    pass


async def send_email(to: list[str], subject: str, html: str, text: str | None = None) -> dict:
    """Send a single email to one or more recipients via Resend's API."""
    if not settings.resend_api_key:
        raise EmailError(
            "RESEND_API_KEY is not configured. Add it to your .env file. "
            "See https://resend.com/docs to get an API key."
        )

    payload = {
        "from": settings.email_from,
        "to": to,
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
        )

    if response.status_code >= 400:
        logger.error("Resend API error %s: %s", response.status_code, response.text)
        raise EmailError(f"Email send failed ({response.status_code}): {response.text}")

    return response.json()


async def send_bulk(recipients: Iterable[str], subject: str, html: str, text: str | None = None) -> dict:
    """Send the same email to many recipients.

    Each recipient gets their own message (using BCC would expose other addresses).
    Resend's API supports up to 50 recipients per call via batching, but for
    simplicity and per-recipient personalization later, we send individually.

    Returns a summary dict: {"sent": int, "failed": int, "errors": list[str]}.
    """
    sent = 0
    failed = 0
    errors: list[str] = []

    for email in recipients:
        try:
            await send_email([email], subject, html, text)
            sent += 1
        except EmailError as e:
            failed += 1
            errors.append(f"{email}: {e}")
            logger.warning("Failed to send to %s: %s", email, e)

    return {"sent": sent, "failed": failed, "errors": errors}
