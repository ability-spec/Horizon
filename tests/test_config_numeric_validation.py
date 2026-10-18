import pytest
from pydantic import ValidationError

from src.models import (
    AIConfig,
    CollectionConfig,
    GDELTConfig,
    GoogleNewsConfig,
    HackerNewsConfig,
    OSSInsightConfig,
    OpenBBWatchlist,
    RedditSubredditConfig,
    RedditUserConfig,
    TelegramChannelConfig,
    TwitterConfig,
)


@pytest.mark.parametrize(
    ("factory", "kwargs"),
    [
        (AIConfig, {"provider": "openai", "model": "test", "api_key_env": "KEY", "max_tokens": 0}),
        (AIConfig, {"provider": "openai", "model": "test", "api_key_env": "KEY", "analysis_concurrency": 0}),
        (CollectionConfig, {"time_window_hours": 0}),
        (HackerNewsConfig, {"fetch_top_stories": 0}),
        (RedditSubredditConfig, {"subreddit": "python", "fetch_limit": 0}),
        (RedditUserConfig, {"username": "example", "fetch_limit": 0}),
        (TelegramChannelConfig, {"channel": "example", "fetch_limit": 0}),
        (TwitterConfig, {"fetch_limit": 0}),
        (OpenBBWatchlist, {"name": "tech", "fetch_limit": 0}),
        (OSSInsightConfig, {"max_items": 0}),
        (GDELTConfig, {"max_records": 251}),
        (GDELTConfig, {"max_records": 0}),
        (GoogleNewsConfig, {"max_results": 0}),
    ],
)
def test_invalid_numeric_limits_are_rejected(factory, kwargs):
    with pytest.raises(ValidationError):
        factory(**kwargs)


def test_zero_comment_limit_remains_valid():
    from src.models import RedditConfig

    assert RedditConfig(fetch_comments=0).fetch_comments == 0
