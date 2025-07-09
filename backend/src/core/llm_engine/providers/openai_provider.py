"""
OpenAI LLM provider implementation
"""
import asyncio
import random
from openai import OpenAI
from src.core.logging import get_logger
from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider"""
    
    def __init__(self, api_key: str, model: str = "gpt-4", **kwargs):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = kwargs.get('max_tokens', 2000)
        self.temperature = kwargs.get('temperature', 0.1)
        self.timeout = kwargs.get('timeout', 30)
        self.retry_count = kwargs.get('retry_count', 5)
        self.retry_backoff_base = kwargs.get('retry_backoff_base', 2)
        self.retry_backoff_max = kwargs.get('retry_backoff_max', 30)
        self.logger = get_logger("openai_provider")

    async def generate_diagnosis(self, prompt: str) -> str:
        """Generate diagnosis using OpenAI API with retry on rate limit"""
        
        for attempt in range(self.retry_count):
            try:
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert software engineer and DevOps specialist. Your job is to analyze error logs and provide detailed diagnosis including root cause analysis and recommendations."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_completion_tokens=self.max_tokens,
                    timeout=self.timeout
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                # Check for OpenAI rate limit error (429)
                is_rate_limit = False
                err_str = str(e)
                if hasattr(e, "status_code") and getattr(e, "status_code", None) == 429:
                    is_rate_limit = True
                elif "rate limit" in err_str.lower() or "429" in err_str:
                    is_rate_limit = True
                if is_rate_limit and attempt < self.retry_count - 1:
                    wait = min(self.retry_backoff_base * (2 ** attempt), self.retry_backoff_max)
                    wait += random.uniform(0, 1)
                    self.logger.warning(f"OpenAI rate limit hit, retrying in {wait:.1f}s (attempt {attempt+1}/{self.retry_count})")
                    await asyncio.sleep(wait)
                    continue
                raise RuntimeError(f"OpenAI API error: {e}")
