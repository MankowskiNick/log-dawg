"""
Base prompt builder interface
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from src.models.schemas import ParsedLogEntry, GitInfo, GitCommitInfo


class BasePromptBuilder(ABC):
    """Abstract base class for prompt builders"""
    
    @abstractmethod
    def build_prompt(self, *args, **kwargs) -> str:
        """Build a prompt string"""
        pass
    
    def _format_prompt_section(self, title: str, content: str, level: int = 2) -> List[str]:
        """Helper method to format a prompt section"""
        header_marker = "#" * level
        return [
            f"{header_marker} {title}",
            "",
            content,
            ""
        ]
    
    def _format_code_block(self, content: str, language: str = "") -> List[str]:
        """Helper method to format a code block"""
        return [
            f"```{language}",
            content,
            "```",
            ""
        ]
    
    def _format_list_items(self, items: List[str], numbered: bool = False) -> List[str]:
        """Helper method to format list items"""
        formatted_items = []
        for i, item in enumerate(items, 1):
            if numbered:
                formatted_items.append(f"{i}. {item}")
            else:
                formatted_items.append(f"- {item}")
        return formatted_items
