"""
Contract tests for LLM module interface.

Verifies that all LLM clients follow the BaseLLMClient interface.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from llm.base import BaseLLMClient
from llm.client import LLMClient, GeminiClient, MistralClient
from core.module import ModuleType


class TestBaseLLMClientInterface:
    """Contract tests for BaseLLMClient interface."""
    
    def test_base_llm_client_inherits_from_module(self):
        """Test that BaseLLMClient inherits from Module."""
        from core.module import Module
        assert issubclass(BaseLLMClient, Module)
    
    def test_base_llm_client_has_required_class_attributes(self):
        """Test BaseLLMClient has required class attributes."""
        assert hasattr(BaseLLMClient, 'name')
        assert hasattr(BaseLLMClient, 'module_type')
        assert hasattr(BaseLLMClient, 'version')
        assert hasattr(BaseLLMClient, 'description')
    
    def test_base_llm_client_module_type_is_llm(self):
        """Test BaseLLMClient has correct module_type."""
        assert BaseLLMClient.module_type == ModuleType.LLM
    
    def test_base_llm_client_has_required_methods(self):
        """Test BaseLLMClient has all required Module methods."""
        required_methods = ['initialize', 'validate', 'execute', 'cleanup']
        for method in required_methods:
            assert hasattr(BaseLLMClient, method), f"Missing method: {method}"
    
    def test_base_llm_client_has_chat_method(self):
        """Test BaseLLMClient has abstract chat method."""
        assert hasattr(BaseLLMClient, 'chat')
    
    def test_base_llm_client_has_request_json_method(self):
        """Test BaseLLMClient has request_json method."""
        assert hasattr(BaseLLMClient, 'request_json')


class TestConcreteLLMClients:
    """Tests for concrete LLM client implementations."""
    
    def test_gemini_client_inherits_from_llm_client(self):
        """Test GeminiClient inherits from LLMClient."""
        assert issubclass(GeminiClient, LLMClient)
    
    def test_gemini_client_inherits_from_base_llm_client(self):
        """Test GeminiClient inherits from BaseLLMClient."""
        assert issubclass(GeminiClient, BaseLLMClient)
    
    def test_gemini_client_has_required_attributes(self):
        """Test GeminiClient has required class attributes."""
        client = GeminiClient()
        assert hasattr(client, 'name')
        assert client.name == "gemini-client"
        assert hasattr(client, 'version')
        assert hasattr(client, 'module_type')
    
    def test_gemini_client_implements_chat(self):
        """Test GeminiClient implements chat method."""
        assert hasattr(GeminiClient, 'chat')
        assert callable(GeminiClient.chat)
    
    @pytest.mark.asyncio
    async def test_gemini_client_chat_is_async(self):
        """Test GeminiClient.chat is async method."""
        client = GeminiClient()
        # Check it's a coroutine function
        import inspect
        assert inspect.iscoroutinefunction(client.chat)
    
    def test_mistral_client_inherits_from_llm_client(self):
        """Test MistralClient inherits from LLMClient."""
        assert issubclass(MistralClient, LLMClient)
    
    def test_mistral_client_inherits_from_base_llm_client(self):
        """Test MistralClient inherits from BaseLLMClient."""
        assert issubclass(MistralClient, BaseLLMClient)
    
    def test_mistral_client_has_required_attributes(self):
        """Test MistralClient has required class attributes."""
        try:
            client = MistralClient()
            assert hasattr(client, 'name')
            assert client.name == "mistral-client"
            assert hasattr(client, 'version')
            assert hasattr(client, 'module_type')
        except ImportError:
            # Mistral library not installed, skip this test
            pytest.skip("Mistral library not installed")


class TestLLMClientFactory:
    """Tests for LLM client factory function."""
    
    def test_get_client_returns_gemini_for_default(self):
        """Test get_client returns GeminiClient by default."""
        from llm.client import get_client
        client = get_client()
        assert isinstance(client, GeminiClient)
    
    def test_get_client_returns_gemini_for_gemini(self):
        """Test get_client returns GeminiClient for 'gemini' backend."""
        from llm.client import get_client
        client = get_client("gemini")
        assert isinstance(client, GeminiClient)
    
    def test_get_client_returns_mistral_for_mistral(self):
        """Test get_client returns MistralClient for 'mistral' backend."""
        from llm.client import get_client
        try:
            client = get_client("mistral")
            assert isinstance(client, MistralClient)
        except ImportError:
            pytest.skip("Mistral library not installed")


class TestLLMClientLifecycle:
    """Tests for LLM client lifecycle methods."""
    
    def test_llm_client_can_be_initialized(self):
        """Test LLMClient can be initialized."""
        client = LLMClient()
        result = client.initialize({})
        assert result is True
        assert client._initialized is True
    
    def test_llm_client_validation(self):
        """Test LLMClient validation."""
        client = LLMClient()
        client.initialize({})
        assert client.validate() is True
        
        client2 = LLMClient()
        assert client2.validate() is False  # Not initialized
    
    def test_llm_client_cleanup(self):
        """Test LLMClient cleanup."""
        client = LLMClient()
        client.initialize({})
        assert client._initialized is True
        
        client.cleanup()
        assert client._initialized is False
    
    @pytest.mark.asyncio
    async def test_llm_client_execute_returns_context(self):
        """Test LLMClient.execute returns context unchanged."""
        from core.module import PipelineContext
        client = LLMClient()
        context = PipelineContext(query="test")
        
        result = await client.execute(context)
        
        assert result is context
