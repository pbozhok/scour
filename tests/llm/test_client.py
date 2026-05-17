"""
Tests for llm.client module.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import subprocess
from llm.client import LLMClient, get_client


class TestLLMClient:
    """Tests for base LLMClient class."""

    def test_llm_client_chat_not_implemented(self):
        """Test that base LLMClient raises NotImplementedError for chat."""
        client = LLMClient()
        with pytest.raises(NotImplementedError):
            asyncio.run(client.chat("test"))

    def test_llm_client_request_json(self):
        """Test request_json method."""
        client = LLMClient()
        client.chat = AsyncMock(return_value='{"key": "value"}')
        result = asyncio.run(client.request_json("test prompt"))
        assert result == {"key": "value"}


class TestGeminiClient:
    """Tests for GeminiClient class."""

    @patch('subprocess.run')
    def test_gemini_client_chat_success(self, mock_run):
        """Test GeminiClient chat with successful response."""
        mock_result = MagicMock()
        mock_result.stdout = "Test response"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        from llm.client import GeminiClient
        client = GeminiClient()
        result = asyncio.run(client.chat("test prompt"))
        assert result == "Test response"

    @patch('subprocess.run')
    def test_gemini_client_chat_empty_response(self, mock_run):
        """Test GeminiClient chat with empty response."""
        mock_result = MagicMock()
        mock_result.stdout = "   "
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        from llm.client import GeminiClient
        client = GeminiClient()
        result = asyncio.run(client.chat("test prompt", max_retries=1))
        assert result == ""

    @patch('subprocess.run')
    def test_gemini_client_chat_timeout(self, mock_run):
        """Test GeminiClient chat with timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("gemini", 30)
        
        from llm.client import GeminiClient
        client = GeminiClient()
        result = asyncio.run(client.chat("test prompt", max_retries=1))
        assert result == ""

    @patch('subprocess.run')
    def test_gemini_client_chat_error(self, mock_run):
        """Test GeminiClient chat with CalledProcessError."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "gemini")
        
        from llm.client import GeminiClient
        client = GeminiClient()
        result = asyncio.run(client.chat("test prompt", max_retries=1))
        assert result == ""

    @patch('subprocess.run')
    def test_gemini_client_chat_retries(self, mock_run):
        """Test GeminiClient chat with retries on failure."""
        # First two calls fail, third succeeds
        mock_result_fail = MagicMock()
        mock_result_fail.stdout = ""
        mock_result_fail.returncode = 1
        
        mock_result_success = MagicMock()
        mock_result_success.stdout = "Success"
        mock_result_success.returncode = 0
        
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "gemini"),
            subprocess.CalledProcessError(1, "gemini"),
            mock_result_success,
        ]
        
        from llm.client import GeminiClient
        client = GeminiClient()
        result = asyncio.run(client.chat("test prompt", max_retries=3))
        assert result == "Success"


class TestGetClient:
    """Tests for get_client factory function."""

    @patch('llm.client.GeminiClient')
    def test_get_client_gemini(self, mock_gemini):
        """Test get_client returns GeminiClient by default."""
        client = get_client("gemini")
        mock_gemini.assert_called_once()

    @patch('llm.client.MistralClient')
    def test_get_client_mistral(self, mock_mistral):
        """Test get_client returns MistralClient for mistral backend."""
        client = get_client("mistral")
        mock_mistral.assert_called_once()

    @patch('llm.client.GeminiClient')
    def test_get_client_default(self, mock_gemini):
        """Test get_client returns GeminiClient for unknown backend."""
        client = get_client("unknown")
        mock_gemini.assert_called_once()
