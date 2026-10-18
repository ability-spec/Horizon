import asyncio
from types import SimpleNamespace

from src.mcp.service import HorizonPipelineService
from src.models import Config


def test_ollama_does_not_require_api_key_environment_variable(tmp_path, monkeypatch):
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    config = Config.model_validate(
        {
            "ai": {"provider": "ollama", "model": "llama3.1", "api_key_env": "OLLAMA_API_KEY"},
            "sources": {},
            "collection": {},
            "digest": {},
        }
    )
    ctx = SimpleNamespace(
        horizon_path=tmp_path,
        config_path=tmp_path / "config.json",
        config=config,
    )
    service = HorizonPipelineService(runs_root=tmp_path / "runs")
    monkeypatch.setattr(service, "_build_context", lambda **kwargs: (ctx, [], []))

    result = asyncio.run(service.validate_config(check_env=True))

    assert "OLLAMA_API_KEY" not in result["missing_env"]
