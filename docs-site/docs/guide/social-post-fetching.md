# Social Post Fetching

The post editor can help researchers create cards from public URLs, but it cannot bypass access controls or anti-bot restrictions. Treat fetched metadata as a starting point and manually edit cards for controlled stimuli.

## What Can Usually Be Fetched

Publicly reachable pages are the best fit:

| Source type | Usually available metadata |
|---|---|
| News articles | Title, description, publisher/source label, Open Graph image, canonical URL. |
| Blogs | Title, description/excerpt, author/site name, hero image. |
| Public institutional pages | Page title, summary, organization name, image if provided. |
| Static public article pages | HTML title, meta description, Open Graph/Twitter card tags. |

Fetched metadata may be incomplete or inaccurate. Always review the title, image, source label, and description before using the card in a study.

## What Usually Cannot Be Fetched

The fetcher should not be expected to retrieve:

| Blocked source | Why |
|---|---|
| Login-only pages | The server has no participant/researcher browser session and should not use private cookies. |
| Private posts or closed groups | Access is intentionally restricted. |
| Paywalled articles | Metadata may be partial, blocked, or legally unsuitable to scrape. |
| JS-only pages | Metadata appears only after client-side rendering, so plain server fetch may see an empty shell. |
| Social apps that block bots | Platforms often restrict automated requests, rate-limit, or omit useful metadata. |
| Personalised feeds | Content depends on a logged-in account, algorithm, location, or session. |

Do not use the fetcher to bypass terms of service, privacy controls, paywalls, or authentication.

## Manual Fallback

When fetching fails or returns weak metadata:

1. Create the post card manually.
2. Enter the study-approved title, description, source label, and display URL.
3. Upload or choose the approved image asset if the app supports it.
4. Set controlled engagement counts.
5. Add comment previews manually.
6. Set More Information behavior according to the study protocol.
7. Preview the card in every target condition and language.

Manual editing is also the right path when the study requires a controlled headline or image that differs from the source page.

## Research Integrity Checks

Before publish:

- Confirm the displayed source label is clear and not misleading.
- Confirm the More Information URL points to the intended public page.
- Confirm fake engagement counts are deliberate stimulus values.
- Confirm comments are researcher-authored or approved study materials.
- Confirm condition-specific overrides are visible only to the intended groups.
