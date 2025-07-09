"""
Base LLM provider interface
"""
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate_diagnosis(self, prompt: str) -> str:
        """Generate diagnosis from prompt"""
        pass
