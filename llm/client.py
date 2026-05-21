"""
LLM Client abstraction for Gemini and Mistral backends.

Provides concrete LLM client implementations that can be used by other modules.
These clients inherit from BaseLLMClient to follow the Module interface.
"""

import asyncio
import os
import subprocess
from typing import Optional

import httpx
from rich.console import Console

from core.logging import get_logger
from llm.base import BaseLLMClient

console = Console()
logger = get_logger(__name__, module_name="llm.client")


class LLMClient(BaseLLMClient):
    """
    Intermediate base class for LLM backends.
    
    Inherits from BaseLLMClient which provides the Module interface.
    This class adds convenience methods that all LLM clients can use.
    """
    
    name: str = "llm-client"
    module_type = None  # Subclasses must set this
    version: str = "1.0.0"
    
    def __init__(self):
        """Initialize the LLM client."""
        self._initialized = False
    
    def initialize(self, config: dict) -> bool:
        """
        Initialize the LLM client with configuration.
        
        Args:
            config: Configuration dictionary
             
        Returns:
            True if initialization succeeded
        """
        self._initialized = True
        return True
    
    def validate(self) -> bool:
        """
        Validate the client is properly configured.
        
        Returns:
            True if valid
        """
        return self._initialized
    
    async def chat(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_retries: int = 5,
    ) -> str:
        """
        Default chat implementation. Subclasses should override this.
        
        Args:
            prompt: The user prompt
            temperature: Sampling temperature
            max_retries: Maximum number of retry attempts
            
        Returns:
            The LLM's response text
            
        Raises:
            NotImplementedError: If subclass doesn't override this method
        """
        raise NotImplementedError("Subclasses must implement chat() method")
    
    async def request_json(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_retries: int = 5,
    ) -> Optional[dict | list]:
        """Send a prompt and extract JSON from response."""
        from utils import extract_json
        response = await self.chat(prompt, temperature, max_retries)
        return extract_json(response)


class GeminiClient(LLMClient):
    """Gemini LLM client using the CLI tool."""
    
    name: str = "gemini-client"
    module_type = None  # LLM clients are service objects, not pipeline stages
    version: str = "1.0.0"
    
    async def chat(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_retries: int = 5,
    ) -> str:
        """
        Use the Gemini CLI to send a prompt and retrieve a response.
        Passes prompt via stdin to avoid command-line length limits.
        Requires 'gemini' command-line tool to be installed.
        """
        for attempt in range(max_retries):
            try:
                # Use stdin instead of --prompt argument to avoid length limits
                command = [
                    "gemini",
                    "--raw-output",
                    "--accept-raw-output-risk",
                ]

                # Execute the command with prompt via stdin
                result = subprocess.run(
                    command, 
                    input=prompt,
                    capture_output=True, 
                    text=True, 
                    timeout=30,  # 30 second timeout
                    check=True
                )

                # Parse and return the response
                response = result.stdout.strip()
                if not response:
                    console.print(f"[yellow]Gemini returned empty response (attempt {attempt + 1})[/yellow]")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return ""
                
                console.print(f"[green]Gemini CLI response:[/green] {response[:100]}...")
                return response

            except subprocess.TimeoutExpired:
                console.print(f"[red]Gemini CLI timeout (attempt {attempt + 1})[/red]")
                if attempt == max_retries - 1:
                    console.print("[red]Max retries reached. Returning empty string.[/red]")
                    return ""
                await asyncio.sleep(2 ** attempt)

            except subprocess.CalledProcessError as e:
                console.print(f"[red]Gemini CLI error (attempt {attempt + 1}): exit code {e.returncode}[/red]")
                if e.stderr:
                    console.print(f"[dim]stderr: {e.stderr[:200]}[/dim]")
                if attempt == max_retries - 1:
                    console.print("[red]Max retries reached. Returning empty string.[/red]")
                    return ""
                await asyncio.sleep(2 ** attempt)

            except Exception as e:
                console.print(f"[red]Unexpected error (attempt {attempt + 1}): {e}[/red]")
                if attempt == max_retries - 1:
                    console.print("[red]Max retries reached. Returning empty string.[/red]")
                    return ""
                await asyncio.sleep(2 ** attempt)

        console.print("[red]Exhausted retries. Returning empty string.[/red]")
        return ""


class MistralClient(LLMClient):
    """Mistral LLM client using the Mistral AI API."""
    
    name: str = "mistral-client"
    module_type = None  # LLM clients are service objects, not pipeline stages
    version: str = "1.0.0"
    
    def __init__(self):
        """Initialize Mistral client, checking API key and library availability."""
        super().__init__()
        try:
            from mistralai.client import Mistral
            self.mistral_module = Mistral
            self.api_key = os.getenv("MISTRAL_API_KEY")
            if not self.api_key:
                console.print("[red]Error: MISTRAL_API_KEY not set in environment[/red]")
        except ImportError:
            console.print("[red]Error: Mistral library not installed.[/red]")
            console.print("[yellow]Install with: pip install mistralai[/yellow]")
            raise
    
    async def chat(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_retries: int = 5,
    ) -> str:
        """Use Mistral AI API to send a prompt and retrieve a response."""
        for attempt in range(max_retries):
            try:
                with self.mistral_module(api_key=self.api_key) as mistral:
                    res = mistral.chat.complete(
                        model="mistral-medium-3-5",
                        messages=[
                            {
                                "role": "user",
                                "content": prompt,
                            },
                        ],
                        stream=False,
                        response_format={"type": "text"},
                        temperature=temperature,
                    )
                    
                    response = res.choices[0].message.content.strip()
                    if not response:
                        console.print(f"[yellow]Mistral returned empty response (attempt {attempt + 1})[/yellow]")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        return ""
                    
                    console.print(f"[green]Mistral API response:[/green] {response[:100]}...")
                    return response

            except Exception as e:
                error_msg = str(e).lower()
                if "quota" in error_msg or "rate limit" in error_msg:
                    console.print(f"[red]Mistral rate limit/quota (attempt {attempt + 1}): {str(e)[:100]}[/red]")
                else:
                    console.print(f"[red]Mistral API error (attempt {attempt + 1}): {str(e)[:100]}[/red]")
                
                if attempt == max_retries - 1:
                    console.print("[red]Max retries reached. Returning empty string.[/red]")
                    return ""
                
                await asyncio.sleep(2 ** attempt)

        console.print("[red]Exhausted retries. Returning empty string.[/red]")
        return ""


def get_client(backend: str = "gemini") -> LLMClient:
    """
    Factory function to get the appropriate LLM client.
    
    Args:
        backend: The LLM backend to use ("gemini" or "mistral")
        
    Returns:
        An instance of the appropriate LLM client
    """
    if backend == "mistral":
        return MistralClient()
    else:
        return GeminiClient()
