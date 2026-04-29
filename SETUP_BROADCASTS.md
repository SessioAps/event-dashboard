# Broadcasting setup guide

This dashboard can email all users about an event and auto-post to LinkedIn.
Both features are optional — the dashboard works without them. Configure only
what you need.

## 1. Email broadcasts (via Resend)

Resend is the easiest modern email provider. You can be sending real emails
in about 3 minutes.

### Setup

1. Sign up at https://resend.com (free).
2. In the dashboard, go to **API Keys** and click **Create API Key**.
   Copy the key (starts with `re_`).
3. In your project root, create a file called `.env` with:

   ```
   RESEND_API_KEY=re_paste_your_key_here
   SECRET_KEY=generate_a_long_random_string
   SITE_URL=http://localhost:8000
   ```

4. Restart the server. The "📧 Email all users" button on each event page now works.

### Sending from your own domain (optional, recommended for production)

By default, Resend only lets you send FROM their sandbox address
`onboarding@resend.dev` to YOUR OWN email address. To send to anyone else:

1. In Resend dashboard → **Domains** → **Add Domain**.
2. Add the DNS records they show you to your domain provider.
3. Once verified (usually a few minutes), update `.env`:

   ```
   EMAIL_FROM=Your Company <events@yourdomain.com>
   ```

## 2. LinkedIn auto-posting

LinkedIn requires a developer app and OAuth, so plan for ~30 minutes of setup.

### Setup

1. Go to https://www.linkedin.com/developers/apps and click **Create app**.
   You'll need to associate it with a LinkedIn Page (your company page).
2. In the **Products** tab, request access to **Share on LinkedIn** and
   **Sign In with LinkedIn using OpenID Connect**. These auto-approve.
3. Go to **Auth** → **OAuth 2.0 tools** → **Generate token**.
   - Select scopes `w_member_social` (post as yourself) and `openid`, `profile`.
   - For posting as your company page instead, also request
     `w_organization_social` and add the **Marketing Developer Platform** product.
4. Copy the access token. Add to `.env`:

   ```
   LINKEDIN_ACCESS_TOKEN=your_token_here
   ```

5. (Only if posting as your company page) Find your organization URN:
   ```
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        https://api.linkedin.com/v2/organizationAcls?q=roleAssignee
   ```
   Look for the `organization` field — it'll be like `urn:li:organization:12345678`.
   Add to `.env`:
   ```
   LINKEDIN_ORGANIZATION_URN=urn:li:organization:12345678
   ```

6. Restart the server. The "📣 Post to social" button on each event page now
   posts to LinkedIn.

### Token expiry

LinkedIn member tokens expire after 60 days. When that happens, the post will
fail with a 401 error — just regenerate the token in the LinkedIn developer
portal and update `.env`.

## 3. Other social platforms

Twitter/X, Facebook, and Instagram are stubbed out in `app/services/social/stubs.py`.
Each has comments explaining what's required. Honest assessment of effort:

- **Twitter/X:** Implementation is short (just a POST to `/2/tweets`), but you
  need a paid API plan ($100/month minimum as of 2024). Skip unless you have
  budget.
- **Facebook Page:** App review process takes 1-2 weeks for the
  `pages_manage_posts` permission. Doable but slow.
- **Instagram:** Requires Business account, Facebook Page link, and you must
  provide an image with every post (text-only not supported).

When you decide to implement one, copy the pattern from `linkedin.py` —
each platform is a self-contained class that the dispatcher calls automatically.

## 4. Public event pages and share buttons

These need zero setup. Every event automatically has a public page at:

```
http://localhost:8000/events/{id}/public
```

This page:
- Has Open Graph meta tags so links shared on WhatsApp, Slack, iMessage,
  Discord, LinkedIn, Twitter, etc. show a rich preview automatically.
- Has share buttons for Twitter/X, LinkedIn, Facebook, WhatsApp, and email.
  Clicking a button opens that platform's compose window pre-filled — no API
  keys, no auth, just works.

For share buttons in production, set `SITE_URL` in `.env` to your real domain
so the URLs in shares aren't `localhost`.
