from backend.core.kiro_gateway import get_gateway_api_key, get_gateway_base_url
from backend.core.llm_providers import KiroGatewayProvider


def test_gateway_config_discovers_parent_env(monkeypatch, tmp_path):
    gateway_root = tmp_path / "kiro-gateway"
    gateway_root.mkdir()
    (gateway_root / ".env").write_text(
        'PROXY_API_KEY="test-proxy-key"\nSERVER_HOST=0.0.0.0\nSERVER_PORT=9010\n',
        encoding="utf-8",
    )

    monkeypatch.setenv("KIRO_GATEWAY_ROOT", str(gateway_root))
    monkeypatch.delenv("KIRO_GATEWAY_API_KEY", raising=False)
    monkeypatch.delenv("PROXY_API_KEY", raising=False)
    monkeypatch.delenv("SERVER_HOST", raising=False)
    monkeypatch.delenv("SERVER_PORT", raising=False)

    assert get_gateway_api_key() == "test-proxy-key"
    assert get_gateway_base_url() == "http://127.0.0.1:9010/v1"


def test_gateway_provider_posts_openai_compatible_payload(monkeypatch):
    captured = {}

    class Response:
        status_code = 200
        text = ""

        def json(self):
            return {
                "model": "claude-sonnet-4-5",
                "choices": [
                    {
                        "message": {"content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"total_tokens": 3},
            }

    def fake_post(url, headers, json, timeout):
        captured.update(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return Response()

    monkeypatch.setattr("requests.post", fake_post)

    provider = KiroGatewayProvider(
        api_key="test-key",
        model_name="claude-sonnet-4-5",
        base_url="http://localhost:8123/v1",
    )
    response = provider.call("Prompt", {"clip": "data"}, temperature=0.1)

    assert response.content == "ok"
    assert captured["url"] == "http://localhost:8123/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "claude-sonnet-4-5"
    assert captured["json"]["stream"] is False
    assert captured["json"]["temperature"] == 0.1
    assert "Prompt" in captured["json"]["messages"][0]["content"]
