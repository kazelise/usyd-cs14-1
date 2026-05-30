"""Fetch Open Graph metadata from a URL.

When a researcher pastes a news link, this service fetches the page
and extracts OG tags (title, image, description, site_name) to
auto-populate the social media post card.
"""

import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

MAX_REDIRECTS = 5

logger = logging.getLogger(__name__)


@dataclass
class OGMetadata:
    title: str | None = None
    image_url: str | None = None
    description: str | None = None
    source: str | None = None  # domain name, e.g. "bbc.com"


def _safe_source(url: str) -> str | None:
    parsed = urlparse(url)
    return parsed.hostname or parsed.netloc or None


def _is_blocked_ip(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return True
    return (
        not ip.is_global
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_private
        or ip.is_reserved
        or ip.is_unspecified
    )


async def _resolve_public_host(hostname: str, port: int) -> bool:
    normalized = hostname.rstrip(".").lower()
    if normalized in {"localhost", "localhost.localdomain"}:
        return False

    try:
        infos = await asyncio.to_thread(
            socket.getaddrinfo,
            hostname,
            port,
            type=socket.SOCK_STREAM,
        )
    except OSError:
        return False

    addresses = {info[4][0] for info in infos}
    return bool(addresses) and all(not _is_blocked_ip(address) for address in addresses)


async def _is_fetchable_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return False
    return await _resolve_public_host(parsed.hostname, port)


async def _safe_get(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
) -> httpx.Response | None:
    current_url = url
    for _ in range(MAX_REDIRECTS + 1):
        if not await _is_fetchable_url(current_url):
            return None

        response = await client.get(current_url, headers=headers, follow_redirects=False)
        if response.is_redirect:
            location = response.headers.get("location")
            if not location:
                return response
            current_url = urljoin(str(response.url), location)
            continue
        return response
    return None


async def fetch_og_metadata(url: str, timeout: float = 10.0) -> OGMetadata:
    """Fetch a URL and extract Open Graph metadata.

    Falls back to regular HTML tags if OG tags are missing.
    """
    metadata = OGMetadata()
    metadata.source = _safe_source(url)  # e.g. "www.bbc.com"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    # trust_env=False: ignore process-level HTTP(S)_PROXY / NO_PROXY env vars.
    # Necessary because some container runtimes (e.g. OrbStack) inject NO_PROXY
    # entries containing bare IPv6 CIDRs, which httpx's URLPattern rejects with
    # InvalidURL during AsyncClient construction. The SSRF guard in
    # _is_fetchable_url is the real security control here; we always egress to
    # public URLs directly.
    try:
        async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
            resp = await _safe_get(client, url, headers)
            if resp is None:
                return metadata
            resp.raise_for_status()
    except Exception as exc:
        logger.warning("og_fetcher: failed to fetch %s: %s: %s", url, type(exc).__name__, exc)
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
