"""
Performance tests for LLM modules.

Validates that LLM modules complete within 10 seconds per spec requirement.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock

from llm.client import get_client
from core.module import PipelineContext


class TestLLMPerformance:
    """Performance tests for LLM modules."""
    
    @pytest.mark.asyncio
    async def test_llm_client_chat_performance(self):
        """Test LLM client chat completes within 10 seconds."""
        client = get_client("gemini")
        
        # Mock the subprocess to avoid actual LLM calls
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "Test response"
            mock_result.stderr = ""
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            start_time = time.time()
            response = await client.chat("Test prompt")
            elapsed = time.time() - start_time
            
            assert elapsed < 10.0, f"LLM chat took {elapsed:.2f}s (target: <10s)"
    
    @pytest.mark.asyncio
    async def test_llm_client_request_json_performance(self):
        """Test LLM client request_json completes within 10 seconds."""
        client = get_client("gemini")
        
        # Mock the subprocess to avoid actual LLM calls
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = '{"key": "value"}'
            mock_result.stderr = ""
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            start_time = time.time()
            response = await client.request_json("Test prompt")
            elapsed = time.time() - start_time
            
            assert elapsed < 10.0, f"LLM request_json took {elapsed:.2f}s (target: <10s)"
    
    @pytest.mark.asyncio
    async def test_llm_client_multiple_calls_performance(self):
        """Test multiple LLM calls complete within 10 seconds total."""
        client = get_client("gemini")
        
        # Mock the subprocess to avoid actual LLM calls
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "Test response"
            mock_result.stderr = ""
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            start_time = time.time()
            
            # Make 3 concurrent calls
            await asyncio.gather(
                client.chat("Prompt 1"),
                client.chat("Prompt 2"),
                client.chat("Prompt 3"),
            )
            
            elapsed = time.time() - start_time
            assert elapsed < 10.0, f"3 LLM calls took {elapsed:.2f}s (target: <10s)"
