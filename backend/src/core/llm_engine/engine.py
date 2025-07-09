"""
Main LLM Engine class
"""
from typing import List, Optional
from src.models.schemas import ParsedLogEntry, DiagnosisResult, GitInfo, GitCommitInfo
from src.core.config import config_manager
from src.core.logging import get_logger
from src.core.context_discovery import ContextDiscoveryEngine
from .providers import LLMProvider, OpenAIProvider, AnthropicProvider, LangfuseProvider
from .prompts import ReportPromptBuilder, JsonFormattingPromptBuilder
from .parsers import JsonResponseParser, ReportResponseParser


class LLMEngine:
    """Main LLM engine for log diagnosis"""
    
    def __init__(self):
        self.config = config_manager.config
        self.settings = config_manager.settings
        self.provider = self._initialize_provider()
        self.context_discovery = ContextDiscoveryEngine(self.provider)
        self.report_prompt_builder = ReportPromptBuilder()
        self.json_prompt_builder = JsonFormattingPromptBuilder()
        self.json_parser = JsonResponseParser()
        self.report_parser = ReportResponseParser()
        self.logger = get_logger("llm_engine")
    
    def _initialize_provider(self) -> LLMProvider:
        """Initialize the configured LLM provider"""
        provider_name = self.config.llm.provider.lower()
        
        if provider_name == "openai":
            if not self.settings.openai_api_key:
                raise ValueError("OpenAI API key is required but not found in environment")
            
            return OpenAIProvider(
                api_key=self.settings.openai_api_key,
                model=self.config.llm.model,
                max_tokens=self.config.llm.max_tokens,
                temperature=self.config.llm.temperature,
                timeout=self.config.llm.timeout,
                retry_count=getattr(self.config.llm, "retry_count", 5),
                retry_backoff_base=getattr(self.config.llm, "retry_backoff_base", 2),
                retry_backoff_max=getattr(self.config.llm, "retry_backoff_max", 30)
            )
        
        elif provider_name == "anthropic":
            if not self.settings.anthropic_api_key:
                raise ValueError("Anthropic API key is required but not found in environment")
            
            return AnthropicProvider(
                api_key=self.settings.anthropic_api_key,
                model=self.config.llm.model,
                max_tokens=self.config.llm.max_tokens,
                temperature=self.config.llm.temperature,
                timeout=self.config.llm.timeout,
                retry_count=getattr(self.config.llm, "retry_count", 5),
                retry_backoff_base=getattr(self.config.llm, "retry_backoff_base", 2),
                retry_backoff_max=getattr(self.config.llm, "retry_backoff_max", 30)
            )
        
        elif provider_name == "langfuse":
            return LangfuseProvider(
                public_key=self.settings.langfuse_public_key,
                secret_key=self.settings.langfuse_secret_key,
                host=self.settings.langfuse_host,
                model=self.config.llm.model,
                max_tokens=self.config.llm.max_tokens,
                temperature=self.config.llm.temperature,
                timeout=self.config.llm.timeout
            )
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_name}")
    
    async def diagnose_log(
        self, 
        parsed_log: ParsedLogEntry, 
        git_info: GitInfo, 
        recent_commits: List[GitCommitInfo] = None,
        diagnosis_id: str = None
    ) -> DiagnosisResult:
        """Generate comprehensive diagnosis for a log entry"""
        self.logger.info(f"[{diagnosis_id}] Starting diagnosis process")

        # Import orchestrator here to avoid circular imports
        from .orchestrator import DiagnosisOrchestrator
        
        orchestrator = DiagnosisOrchestrator(
            provider=self.provider,
            context_discovery=self.context_discovery,
            report_prompt_builder=self.report_prompt_builder,
            json_prompt_builder=self.json_prompt_builder,
            json_parser=self.json_parser,
            report_parser=self.report_parser,
            config=self.config,
            logger=self.logger
        )
        
        return await orchestrator.orchestrate_diagnosis(
            parsed_log=parsed_log,
            git_info=git_info,
            recent_commits=recent_commits,
            diagnosis_id=diagnosis_id
        )
