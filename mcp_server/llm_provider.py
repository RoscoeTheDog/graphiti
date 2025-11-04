"""
LLM Provider Abstraction for Memory Filter System

Provides a unified interface for different LLM providers (OpenAI, Anthropic)
with hierarchical fallback support.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import os
import logging

from mcp_server.unified_config import LLMFilterProviderConfig

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, config: LLMFilterProviderConfig):
        self.config = config
        self.api_key = config.api_key

    @abstractmethod
    async def complete(self, prompt: str) -> Dict[str, Any]:
        """Send prompt to LLM and return parsed response"""
        pass

    def is_available(self) -> bool:
        """Check if provider is configured and enabled"""
        return self.config.enabled and self.api_key is not None and hasattr(self, 'client') and self.client is not None


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider"""

    def __init__(self, config: LLMFilterProviderConfig):
        super().__init__(config)
        if self.api_key:
            try:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                logger.warning("openai library not installed - OpenAI provider unavailable")
                self.client = None
        else:
            self.client = None

    async def complete(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API"""
        if not self.client:
            raise ValueError("OpenAI client not initialized - API key missing")

        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                response_format={"type": "json_object"}
            )

            import json
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


class AnthropicProvider(LLMProvider):
    """Anthropic LLM provider"""

    def __init__(self, config: LLMFilterProviderConfig):
        super().__init__(config)
        if self.api_key:
            try:
                from anthropic import AsyncAnthropic
                self.client = AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                logger.warning("anthropic library not installed - Anthropic provider unavailable")
                self.client = None
        else:
            self.client = None

    async def complete(self, prompt: str) -> Dict[str, Any]:
        """Call Anthropic API"""
        if not self.client:
            raise ValueError("Anthropic client not initialized - API key missing")

        try:
            response = await self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract JSON from response
            import json
            content = response.content[0].text

            # Try to extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


def create_provider(config: LLMFilterProviderConfig) -> LLMProvider:
    """Factory function to create LLM provider"""
    if config.name == "openai":
        return OpenAIProvider(config)
    elif config.name == "anthropic":
        return AnthropicProvider(config)
    else:
        raise ValueError(f"Unknown provider: {config.name}")
