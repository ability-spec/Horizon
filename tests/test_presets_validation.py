from src.setup import presets


def test_fetch_presets_returns_none_for_malformed_json_shape(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"categories": [None]}

    monkeypatch.setattr(presets.httpx, "get", lambda *args, **kwargs: FakeResponse())

    assert presets.fetch_presets() is None
