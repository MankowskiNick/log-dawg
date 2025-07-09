"""
Anthropic LLM provider implementation
"""
import asyncio
import random
from anthropic import Anthropic
from src.core.logging import get_logger
from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider"""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229", **kwargs):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = kwargs.get('max_tokens', 2000)
        self.temperature = kwargs.get('temperature', 0.1)
        self.timeout = kwargs.get('timeout', 30)
        self.retry_count = kwargs.get('retry_count', 5)
        self.retry_backoff_base = kwargs.get('retry_backoff_base', 2)
        self.retry_backoff_max = kwargs.get('retry_backoff_max', 30)
        self.logger = get_logger("anthropic_provider")

    async def generate_diagnosis(self, prompt: str) -> str:
        """Generate diagnosis using Anthropic API with retry on rate limit"""
        
        for attempt in range(self.retry_count):
            try:
                response = await asyncio.to_thread(
                    self.client.messages.create,
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    timeout=self.timeout,
                    system="You are an expert software engineer and DevOps specialist. Your job is to analyze error logs and provide detailed diagnosis including root cause analysis and recommendations.",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                return response.content[0].text.strip()
            except Exception as e:
                # Check for Anthropic rate limit error (429)
                is_rate_limit = False
                err_str = str(e)
                if hasattr(e, "status_code") and getattr(e, "status_code", None) == 429:
                    is_rate_limit = True
                elif "rate limit" in err_str.lower() or "429" in err_str:
                    is_rate_limit = True
                
                if is_rate_limit and attempt < self.retry_count - 1:
                    wait = min(self.retry_backoff_base * (2 ** attempt), self.retry_backoff_max)
                    wait += random.uniform(0, 1)
                    self.logger.warning(f"Anthropic rate limit hit, retrying in {wait:.1f}s (attempt {attempt+1}/{self.retry_count})")
                    await asyncio.sleep(wait)
                    continue
                raise RuntimeError(f"Anthropic API error: {e}")
