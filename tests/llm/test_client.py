"""
Tests for llm.client module.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from llm.client import LLMClient, get_client


def _make_proc(stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0):
    """Build a mock async subprocess."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.kill = MagicMock()
    return proc


class TestLLMClient:

    def test_llm_client_chat_not_implemented(self):
        client = LLMClient()
        with pytest.raises(NotImplementedError):
            asyncio.run(client.chat("test"))

    def test_llm_client_request_json(self):
        client = LLMClient()
        client.chat = AsyncMock(return_value='{"key": "value"}')
        result = asyncio.run(client.request_json("test prompt"))
        assert result == {"key": "value"}


class TestGeminiClient:

    @patch('asyncio.create_subprocess_exec')
    def test_gemini_client_chat_success(self, mock_create):
        mock_create.return_value = _make_proc(stdout=b"Test response")
        from llm.client import GeminiClient
        result = asyncio.run(GeminiClient().chat("test prompt"))
        assert result == "Test response"

    @patch('asyncio.create_subprocess_exec')
    def test_gemini_client_chat_empty_response(self, mock_create):
        mock_create.return_value = _make_proc(stdout=b"   ")
        from llm.client import GeminiClient
        result = asyncio.run(GeminiClient().chat("test prompt", max_retries=1))
        assert result == ""

    @patch('asyncio.create_subprocess_exec')
    def test_gemini_client_chat_timeout(self, mock_create):
        proc = MagicMock()
        proc.kill = MagicMock()
        proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
        mock_create.return_value = proc
        from llm.client import GeminiClient
        result = asyncio.run(GeminiClient().chat("test prompt", max_retries=1))
        assert result == ""

    @patch('asyncio.create_subprocess_exec')
    def test_gemini_client_chat_error(self, mock_create):
        mock_create.return_value = _make_proc(returncode=1, stderr=b"error")
        from llm.client import GeminiClient
        result = asyncio.run(GeminiClient().chat("test prompt", max_retries=1))
        assert result == ""

    @patch('asyncio.create_subprocess_exec')
    def test_gemini_client_chat_retries(self, mock_create):
        fail = _make_proc(returncode=1, stderr=b"err")
        success = _make_proc(stdout=b"Success")
        mock_create.side_effect = [fail, fail, success]
        from llm.client import GeminiClient
        result = asyncio.run(GeminiClient().chat("test prompt", max_retries=3))
        assert result == "Success"


class TestGetClient:

    @patch('llm.client.GeminiClient')
    def test_get_client_gemini(self, mock_gemini):
        get_client("gemini")
        mock_gemini.assert_called_once()

    @patch('llm.client.MistralClient')
    def test_get_client_mistral(self, mock_mistral):
        get_client("mistral")
        mock_mistral.assert_called_once()

    @patch('llm.client.GeminiClient')
    def test_get_client_default(self, mock_gemini):
        get_client("unknown")
        mock_gemini.assert_called_once()
