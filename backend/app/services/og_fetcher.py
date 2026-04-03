"""Fetch Open Graph metadata from a URL.

When a researcher pastes a news link, this service fetches the page
and extracts OG tags (title, image, description, site_name) to
auto-populate the social media post card.
"""

from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


@dataclass
class OGMetadata:
    title: str | None = None
    image_url: str | None = None
    description: str | None = None
    source: str | None = None  # domain name, e.g. "bbc.com"


async def fetch_og_metadata(url: str, timeout: float = 10.0) -> OGMetadata:
    """Fetch a URL and extract Open Graph metadata.

    Falls back to regular HTML tags if OG tags are missing.
    """
    metadata = OGMetadata()
    metadata.source = urlparse(url).netloc  # e.g. "www.bbc.com"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
    except Exception:
        return metadata  # return partial metadata with just the domain

    soup = BeautifulSoup(resp.text, "html.parser")

    # Try OG tags first, then fall back to regular HTML
    og_title = soup.find("meta", property="og:title")
    metadata.title = (
        og_title["content"]
        if og_title and og_title.get("content")
        else (soup.title.string if soup.title else None)
    )

    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        metadata.image_url = og_image["content"]

    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        metadata.description = og_desc["content"]
    else:
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            metadata.description = meta_desc["content"]

    og_site = soup.find("meta", property="og:site_name")
    if og_site and og_site.get("content"):
        metadata.source = og_site["content"]

    return metadata
