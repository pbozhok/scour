"""
Integration tests for LLM module functionality.

Tests that LLM clients work correctly in the context of the full pipeline.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from core.pipeline import Pipeline, PipelineConfig
from core.module import PipelineContext, ModuleType
from llm.client import get_client, GeminiClient


class TestLLMPipelineIntegration:
    """Integration tests for LLM clients in the pipeline."""
    
    def test_llm_providers_config_exists(self):
        """Test that LLM_PROVIDERS config is defined."""
        from config import LLM_PROVIDERS
        assert "gemini" in LLM_PROVIDERS
        assert "mistral" in LLM_PROVIDERS
    
    def test_get_client_uses_llm_providers_config(self):
        """Test that get_client uses the LLM_PROVIDERS config."""
        from config import LLM_PROVIDERS
        
        # Verify the config maps to the correct classes
        assert LLM_PROVIDERS["gemini"] == "llm.client.GeminiClient"
        assert LLM_PROVIDERS["mistral"] == "llm.client.MistralClient"
    
    @pytest.mark.asyncio
    async def test_pipeline_config_includes_llm_backend(self):
        """Test that PipelineConfig includes llm_backend setting."""
        config = PipelineConfig(
            query="test",
            llm_backend="gemini"
        )
        assert config.llm_backend == "gemini"
        assert config.to_dict()["llm_backend"] == "gemini"
    
    @pytest.mark.asyncio
    async def test_pipeline_config_includes_all_llm_settings(self):
        """Test that PipelineConfig includes all relevant LLM settings."""
        config = PipelineConfig(
            query="test",
            llm_backend="mistral",
            skip_filter=False,
            skip_score=False,
            skip_reviews=False
        )
        config_dict = config.to_dict()
        assert "llm_backend" in config_dict
        assert config_dict["llm_backend"] == "mistral"


class TestLLMFilterIntegration:
    """Integration tests for LLM filter with different backends."""
    
    @pytest.mark.asyncio
    async def test_llm_filter_initialization_with_gemini(self):
        """Test LLMFilter can be initialized with Gemini backend."""
        from filters.llm_filter import LLMFilter
        
        llm_filter = LLMFilter(llm_backend="gemini")
        config = {"llm_backend": "gemini", "debug": False}
        
        result = llm_filter.initialize(config)
        assert result is True
        assert llm_filter._llm_client is not None
        assert isinstance(llm_filter._llm_client, GeminiClient)
    
    @pytest.mark.asyncio
    async def test_llm_filter_validation_with_client(self):
        """Test LLMFilter validation with initialized client."""
        from filters.llm_filter import LLMFilter
        
        llm_filter = LLMFilter()
        config = {"llm_backend": "gemini", "debug": False}
        llm_filter.initialize(config)
        
        assert llm_filter.validate() is True
    
    @pytest.mark.asyncio
    async def test_llm_filter_without_initialization(self):
        """Test LLMFilter validation without initialization."""
        from filters.llm_filter import LLMFilter
        
        llm_filter = LLMFilter()
        assert llm_filter.validate() is False


class TestModelExtractorIntegration:
    """Integration tests for ModelExtractor with different backends."""
    
    @pytest.mark.asyncio
    async def test_model_extractor_initialization_with_gemini(self):
        """Test ModelExtractor can be initialized with Gemini backend."""
        from processors.model_extractor import ModelExtractor
        
        extractor = ModelExtractor(llm_backend="gemini")
        config = {"llm_backend": "gemini", "debug": False}
        
        result = extractor.initialize(config)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_model_extractor_validation(self):
        """Test ModelExtractor validation."""
        from processors.model_extractor import ModelExtractor
        
        extractor = ModelExtractor(llm_backend="gemini")
        config = {"llm_backend": "gemini", "debug": False}
        extractor.initialize(config)
        
        assert extractor.validate() is True


class TestLLMBackendSwapping:
    """Tests for swapping LLM backends at runtime."""
    
    def test_switch_from_gemini_to_gemini(self):
        """Test switching from gemini to gemini (no-op)."""
        client1 = get_client("gemini")
        client2 = get_client("gemini")
        
        # Should get new instances each time (not singleton)
        assert isinstance(client1, GeminiClient)
        assert isinstance(client2, GeminiClient)
    
    @patch.dict('os.environ', {'MISTRAL_API_KEY': 'test-key'}, clear=False)
    @patch('mistralai.client.Mistral')
    def test_switch_to_mistral(self, mock_mistral):
        """Test switching to Mistral backend."""
        try:
            from llm.client import MistralClient
            client = get_client("mistral")
            assert isinstance(client, MistralClient)
        except ImportError:
            pytest.skip("Mistral library not installed")
