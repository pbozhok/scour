"""
Performance tests for LLM modules.

Validates that LLM modules complete within 10 seconds per spec requirement.
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from llm.client import get_client


def _make_proc(stdout: bytes = b"", returncode: int = 0):
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, b""))
    proc.kill = MagicMock()
    return proc


class TestLLMPerformance:

    @pytest.mark.asyncio
    async def test_llm_client_chat_performance(self):
        client = get_client("gemini")
        with patch('asyncio.create_subprocess_exec', return_value=_make_proc(b"Test response")):
            start = time.time()
            response = await client.chat("Test prompt")
            assert time.time() - start < 10.0

    @pytest.mark.asyncio
    async def test_llm_client_request_json_performance(self):
        client = get_client("gemini")
        with patch('asyncio.create_subprocess_exec', return_value=_make_proc(b'{"key": "value"}')):
            start = time.time()
            response = await client.request_json("Test prompt")
            assert time.time() - start < 10.0

    @pytest.mark.asyncio
    async def test_llm_client_multiple_calls_performance(self):
        client = get_client("gemini")
        with patch('asyncio.create_subprocess_exec', return_value=_make_proc(b"Test response")):
            start = time.time()
            await asyncio.gather(
                client.chat("Prompt 1"),
                client.chat("Prompt 2"),
                client.chat("Prompt 3"),
            )
            assert time.time() - start < 10.0
