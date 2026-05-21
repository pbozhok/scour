"""
Base LLM client class with common functionality for all LLM providers.

All LLM clients must inherit from this class which implements the Module interface.
"""

from abc import abstractmethod
from typing import Optional, Dict, Any

from core.module import Module, ModuleType, PipelineContext


class BaseLLMClient(Module):
    """
    Base class for all LLM clients.
    
    Inherits from Module and implements the LLM-specific interface.
    All LLM clients (Gemini, Mistral, Anthropic) must inherit from this class.
    """
    
    name: str = "base-llm"
    module_type: ModuleType = ModuleType.LLM
    version: str = "1.0.0"
    
    def __init__(self):
        self._initialized = False
        self._api_key: Optional[str] = None
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the LLM client with API key and configuration.
        
        Args:
            config: Configuration dictionary containing api_key
            
        Returns:
            True if initialization succeeded
        """
        self._api_key = config.get("api_key")
        self._initialized = bool(self._api_key)
        return self._initialized
    
    def validate(self) -> bool:
        """
        Validate the client is properly configured.
        
        Returns:
            True if API key is set
        """
        return self._initialized and bool(self._api_key)
    
    def cleanup(self) -> None:
        """Clean up any resources."""
        self._api_key = None
        self._initialized = False
    
    @abstractmethod
    async def chat(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_retries: int = 5,
    ) -> str:
        """
        Send a chat prompt to the LLM and get a response.
        
        Args:
            prompt: The user prompt
            temperature: Sampling temperature (0.0 to 1.0)
            max_retries: Maximum number of retry attempts
            
        Returns:
            The LLM's response text
        """
        pass
    
    async def request_json(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_retries: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """
        Send a prompt and extract JSON from the response.
        
        Args:
            prompt: The user prompt
            temperature: Sampling temperature
            max_retries: Maximum number of retry attempts
            
        Returns:
            Parsed JSON dict, or None if parsing fails
        """
        from utils import extract_json
        response = await self.chat(prompt, temperature, max_retries)
        return extract_json(response)
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute the LLM module (typically not called directly).
        
        LLM clients are usually used as dependencies by other modules
        (filters, rankers, reviewers) rather than as pipeline modules themselves.
        
        Args:
            context: The pipeline context (not typically used for LLM)
            
        Returns:
            Context unchanged (LLM clients are service objects, not pipeline stages)
        """
        # LLM clients are injected as dependencies, not executed as pipeline stages
        return context
