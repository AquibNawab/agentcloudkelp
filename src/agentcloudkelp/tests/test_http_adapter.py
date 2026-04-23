from __future__ import annotations

import pytest
import httpx

from ..adapters.http import HTTPAdapter


class _SuccessClient:
    def __init__(self, response):
        self.response = response
        self.request = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url, json):
        self.request = {"url": url, "json": json}
        return self.response


class _TimeoutClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, *args, **kwargs):
        raise httpx.TimeoutException("timed out")


class _ErrorClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, *args, **kwargs):
        request = httpx.Request("POST", "https://example.com/chat")
        return httpx.Response(500, text="boom", request=request)


@pytest.mark.asyncio
async def test_http_adapter_parses_response_with_field_mappings(monkeypatch):
    payload = {
        "assistant_text": "Flight booked successfully.",
        "calls": [
            {
                "name": "create_booking",
                "arguments": {"flight_id": "AB123"},
                "result": {"booking_id": "BK1"},
                "duration_ms": 12.5,
            }
        ],
        "in_tokens": 42,
        "out_tokens": 18,
        "latency": 250.0,
        "trace": {"request_id": "abc-123"},
    }
    response = httpx.Response(200, json=payload, request=httpx.Request("POST", "https://example.com/chat"))
    client = _SuccessClient(response)
    monkeypatch.setattr("agentcloudkelp.adapters.http.httpx.AsyncClient", lambda *a, **kw: client)

    adapter = HTTPAdapter(
        "https://example.com/chat",
        headers={"x-api-key": "secret"},
        field_mappings={
            "response": "assistant_text",
            "tool_calls": "calls",
            "input_tokens": "in_tokens",
            "output_tokens": "out_tokens",
            "latency_ms": "latency",
            "raw_trace": "trace",
        },
    )

    result = await adapter.send_message("Book my flight", [{"role": "user", "content": "hi"}])

    assert client.request == {
        "url": "https://example.com/chat",
        "json": {"message": "Book my flight", "context": [{"role": "user", "content": "hi"}]},
    }
    assert result.response == "Flight booked successfully."
    assert result.tool_calls[0].name == "create_booking"
    assert result.tool_calls[0].arguments == {"flight_id": "AB123"}
    assert result.token_usage.input_tokens == 42
    assert result.token_usage.output_tokens == 18
    assert result.latency_ms == 250.0
    assert result.raw_trace == {"request_id": "abc-123"}


@pytest.mark.asyncio
async def test_http_adapter_timeout(monkeypatch):
    monkeypatch.setattr("agentcloudkelp.adapters.http.httpx.AsyncClient", lambda *a, **kw: _TimeoutClient())

    adapter = HTTPAdapter("https://example.com/chat")

    with pytest.raises(RuntimeError, match="timeout"):
        await adapter.send_message("hi", [])


@pytest.mark.asyncio
async def test_http_adapter_http_error(monkeypatch):
    monkeypatch.setattr("agentcloudkelp.adapters.http.httpx.AsyncClient", lambda *a, **kw: _ErrorClient())

    adapter = HTTPAdapter("https://example.com/chat")

    with pytest.raises(RuntimeError, match="status 500"):
        await adapter.send_message("hi", [])
