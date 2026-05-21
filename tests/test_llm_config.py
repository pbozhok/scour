"""
Tests for LLM client configuration and swapping.

Verifies that LLM clients can be swapped via configuration.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from llm.client import get_client, GeminiClient, MistralClient
from core.module import PipelineContext


class TestLLMClientSwapping:
    """Tests for swapping LLM clients via configuration."""
    
    def test_get_client_with_gemini_config(self):
        """Test that get_client returns GeminiClient when configured."""
        client = get_client("gemini")
        assert isinstance(client, GeminiClient)
    
    def test_get_client_with_mistral_config(self):
        """Test that get_client returns MistralClient when configured."""
        try:
            client = get_client("mistral")
            assert isinstance(client, MistralClient)
        except ImportError:
            pytest.skip("Mistral library not installed")
    
    def test_get_client_default_is_gemini(self):
        """Test that get_client defaults to GeminiClient."""
        client = get_client()
        assert isinstance(client, GeminiClient)
    
    def test_get_client_unknown_backend_defaults_to_gemini(self):
        """Test that unknown backend defaults to GeminiClient."""
        client = get_client("unknown_backend")
        assert isinstance(client, GeminiClient)


class TestLLMConfigIntegration:
    """Integration tests for LLM configuration in modules."""
    
    @pytest.mark.asyncio
    async def test_filter_uses_configured_llm_backend(self):
        """Test that LLMFilter uses the configured LLM backend."""
        from filters.llm_filter import LLMFilter
        from core.module import PipelineContext
        
        # Create filter with gemini backend
        llm_filter = LLMFilter(llm_backend="gemini")
        config = {"llm_backend": "gemini", "debug": False}
        llm_filter.initialize(config)
        
        # Check that the client is a GeminiClient
        assert llm_filter._llm_client is not None
        assert isinstance(llm_filter._llm_client, GeminiClient)
    
    @pytest.mark.asyncio
    async def test_module_initialization_with_llm_config(self):
        """Test that modules can initialize with LLM backend config."""
        from processors.model_extractor import ModelExtractor
        
        # Create extractor with gemini backend
        extractor = ModelExtractor(llm_backend="gemini")
        config = {"llm_backend": "gemini", "debug": False}
        
        result = extractor.initialize(config)
        
        # Should succeed with gemini
        assert result is True


class TestLLMInDependencyContainer:
    """Tests for LLM clients in the DI container."""
    
    def test_llm_client_bound_in_container(self):
        """Test that LLMClient is bound in the DI container."""
        from core.injection import container, register_llm_providers
        from llm.client import LLMClient
        
        # Need to register LLM providers explicitly to avoid circular imports
        register_llm_providers()
        
        assert container.has_binding(LLMClient)
    
    def test_get_llm_client_from_container(self):
        """Test getting LLM client from container."""
        from core.injection import container, register_llm_providers
        from llm.client import LLMClient
        from llm.base import BaseLLMClient
        
        # Need to register LLM providers explicitly to avoid circular imports
        register_llm_providers()
        
        # Get an LLM client from the container
        # Note: The factory function get_client needs a backend parameter
        # This test verifies the binding exists
        assert container.has_binding(BaseLLMClient)
