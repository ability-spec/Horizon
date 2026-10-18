from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from src.models import RSSSourceConfig
from src.scrapers.rss import RSSScraper

_FEED = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0"><channel><title>Test</title>
  <item>
    <guid>entry-1</guid>
    <title>Item 1</title>
    <link>https://example.com/item-1</link>
    <pubDate>Fri, 24 Apr 2026 12:00:00 GMT</pubDate>
    <description>Short summary from feed.</description>
  </item>
</channel></rss>
"""
_SINCE = datetime(2026, 4, 24, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _mock_public_dns(monkeypatch) -> None:
    async def resolve(hostname: str, port: int) -> set[str]:
        return {"93.184.216.34"}

    monkeypatch.setattr("src.url_security._resolve_hostname", resolve)


def _make_feed_client(feed_text: str) -> AsyncMock:
    response = MagicMock()
    response.text = feed_text
    response.raise_for_status.return_value = None
    client = AsyncMock()
    client.get.return_value = response
    return client


def test_rss_ids_are_deterministic() -> None:
    client = _make_feed_client(_FEED)
    source = RSSSourceConfig(
        name="Test", url="https://example.com/feed.xml", profile="rss-profile"
    )
    scraper = RSSScraper([source], client)

    first_item = asyncio.run(scraper.fetch(_SINCE))[0]
    first = first_item.id
    second = asyncio.run(scraper.fetch(_SINCE))[0].id

    assert first == second
    assert first == "rss:example.com_feed.xml:5e2d5d1e58e94d76"
    assert first_item.profile == "rss-profile"


def test_timezone_less_pubdate_is_treated_as_utc() -> None:
    client = _make_feed_client(_FEED.replace(" GMT", ""))
    source = RSSSourceConfig(name="Test", url="https://example.com/feed.xml")
    scraper = RSSScraper([source], client)

    items = asyncio.run(scraper.fetch(_SINCE))

    assert len(items) == 1
    assert items[0].published_at == datetime(
        2026, 4, 24, 12, 0, tzinfo=timezone.utc
    )


def _make_registry(name: str, extractor):
    registry = MagicMock()
    registry.get.side_effect = lambda n: extractor if n == name else None
    return registry


def test_content_extractor_replaces_feed_content() -> None:
    client = _make_feed_client(_FEED)
    extractor = AsyncMock()
    extractor.extract.return_value = "Full article text from extractor."

    source = RSSSourceConfig(
        name="Test", url="https://example.com/feed.xml", content_extractor="my-ext"
    )
    scraper = RSSScraper([source], client, extractors=_make_registry("my-ext", extractor))
    items = asyncio.run(scraper.fetch(_SINCE))

    assert len(items) == 1
    assert items[0].content == "Full article text from extractor."
    extractor.extract.assert_awaited_once_with("https://example.com/item-1", client)


def test_content_extractor_falls_back_on_none() -> None:
    client = _make_feed_client(_FEED)
    extractor = AsyncMock()
    extractor.extract.return_value = None  # extraction failed

    source = RSSSourceConfig(
        name="Test", url="https://example.com/feed.xml", content_extractor="my-ext"
    )
    scraper = RSSScraper([source], client, extractors=_make_registry("my-ext", extractor))
    items = asyncio.run(scraper.fetch(_SINCE))

    assert len(items) == 1
    assert items[0].content == "Short summary from feed."


def test_unknown_extractor_name_ignored() -> None:
    client = _make_feed_client(_FEED)
    source = RSSSourceConfig(
        name="Test", url="https://example.com/feed.xml", content_extractor="nonexistent"
    )
    scraper = RSSScraper([source], client, extractors=_make_registry("other", AsyncMock()))
    items = asyncio.run(scraper.fetch(_SINCE))

    assert len(items) == 1
    assert items[0].content == "Short summary from feed."

def test_rss_uses_safe_request_for_feed() -> None:
    client = _make_feed_client(_FEED)
    source = RSSSourceConfig(name="Test", url="https://example.com/feed.xml")
    scraper = RSSScraper([source], client)

    items = asyncio.run(scraper.fetch(_SINCE))

    assert len(items) == 1
    assert client.get.await_args.kwargs["follow_redirects"] is False


def test_rss_skips_invalid_entry_and_keeps_later_valid_entry() -> None:
    feed_text = (
        '<?xml version="1.0" encoding="UTF-8" ?>'
        '<rss version="2.0"><channel><title>Test</title>'
        '<item><guid>bad</guid><title>Bad URL</title>'
        '<link>javascript:alert(1)</link>'
        '<pubDate>Fri, 24 Apr 2026 12:00:00 GMT</pubDate></item>'
        '<item><guid>good</guid><title>Good item</title>'
        '<link>https://example.com/good</link>'
        '<pubDate>Fri, 24 Apr 2026 12:01:00 GMT</pubDate></item>'
        '</channel></rss>'
    )
    client = _make_feed_client(feed_text)
    source = RSSSourceConfig(name="Test", url="https://example.com/feed.xml")

    items = asyncio.run(RSSScraper([source], client).fetch(_SINCE))

    assert [item.title for item in items] == ["Good item"]
