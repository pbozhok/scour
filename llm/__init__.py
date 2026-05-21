"""
LLM module for abstracting different LLM backends.

This module provides LLM client implementations for the second-hand research agent.
All LLM clients inherit from BaseLLMClient which implements the Module interface.

Available LLM clients:
- GeminiClient: Uses Google Gemini CLI tool
- MistralClient: Uses Mistral AI API

Factory function:
- get_client(backend): Returns the appropriate LLM client for the specified backend

Usage:
    from llm import get_client
    
    # Get a client based on configuration
    llm_client = get_client("gemini")  # or "mistral"
    
    # Use the client
    response = await llm_client.chat("Tell me about iPhone 15")
    
    # Or get JSON response
    data = await llm_client.request_json("Return JSON data")
"""

from .base import BaseLLMClient
from .client import LLMClient, GeminiClient, MistralClient, get_client

__all__ = ["BaseLLMClient", "LLMClient", "GeminiClient", "MistralClient", "get_client"]
