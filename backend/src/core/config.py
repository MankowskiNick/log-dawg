"""
Configuration management for Log Dawg
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class RepositoryConfig(BaseModel):
    url: str
    branch: str = "main"
    local_path: str = "./repo"
    auth_method: str = "ssh"


class LLMConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4"
    max_tokens: int = 2000
    temperature: float = 0.1
    timeout: int = 30


class ReportsConfig(BaseModel):
    output_dir: str = "./reports"
    max_reports: int = 100
    filename_format: str = "diagnosis_{timestamp}_{hash}.md"
    include_git_diff: bool = True
    max_git_commits: int = 10


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    http_workers: int = 1


class LogProcessingConfig(BaseModel):
    max_log_size_mb: int = 10
    supported_formats: List[str] = ["json", "text", "cloudwatch"]
    extract_patterns: List[str] = ["ERROR", "FATAL", "CRITICAL", "Exception", "Traceback"]


class GitAnalysisConfig(BaseModel):
    include_recent_commits: bool = True
    max_commits_to_analyze: int = 5
    file_extensions_to_include: List[str] = [".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp", ".c"]

class LLMInteractionLoggingConfig(BaseModel):
    log_requests: bool = True
    log_responses: bool = True
    truncate_large_responses: bool = True
    max_prompt_log_length: int = 2000
    max_response_log_length: int = 2000

class ContextDiscoveryConfig(BaseModel):
    enabled: bool = True
    max_iterations: int = 3
    confidence_threshold: float = 0.8
    file_size_limit_kb: int = 100
    max_total_context_size_kb: int = 500
    file_extensions_priority: List[str] = [".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp", ".c"]
    exclude_patterns: List[str] = ["*.log", "*.tmp", "node_modules/*", "__pycache__/*", ".git/*"]
    prioritize_recent_changes: bool = True
    min_confidence_improvement: float = 0.1

class LoggingConfig(BaseModel):
    level: str = "INFO"
    per_diagnosis_logging: bool = True
    log_directory: str = "./logs"
    retention_days: int = 30
    max_log_size_mb: int = 100
    structured_format: bool = True
    console_logging: bool = True
    file_logging: bool = True
    include_performance_metrics: bool = True
    llm_interaction_logging: LLMInteractionLoggingConfig = LLMInteractionLoggingConfig()


class AppConfig(BaseModel):
    repository: RepositoryConfig
    llm: LLMConfig
    reports: ReportsConfig
    server: ServerConfig
    log_processing: Optional[LogProcessingConfig] = None
    git_analysis: GitAnalysisConfig
    context_discovery: ContextDiscoveryConfig = ContextDiscoveryConfig()
    logging: LoggingConfig = LoggingConfig()


class Settings(BaseSettings):
    """Environment-based settings"""
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    git_token: str = Field(default="", env="GIT_TOKEN")
    git_username: str = Field(default="", env="GIT_USERNAME")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Optional Langfuse settings
    langfuse_public_key: str = Field(default="", env="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", env="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="", env="LANGFUSE_HOST")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class ConfigManager:
    """Manages application configuration"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self.settings = Settings()
        self._config = None
        self.load_config()
    
    def load_config(self) -> AppConfig:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        self._config = AppConfig(**config_data)
        return self._config
    
    @property
    def config(self) -> AppConfig:
        """Get the current configuration"""
        if self._config is None:
            self.load_config()
        return self._config
    
    def reload_config(self) -> AppConfig:
        """Reload configuration from file"""
        return self.load_config()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get environment setting by key"""
        return getattr(self.settings, key, default)
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate current configuration and return status"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required API keys
        if self.config.llm.provider == "openai" and not self.settings.openai_api_key:
            validation_result["errors"].append("OpenAI API key is required when using OpenAI provider")
            validation_result["valid"] = False
        
        if self.config.llm.provider == "anthropic" and not self.settings.anthropic_api_key:
            validation_result["errors"].append("Anthropic API key is required when using Anthropic provider")
            validation_result["valid"] = False
        
        if self.config.llm.provider == "langfuse":
            if not self.settings.langfuse_public_key:
                validation_result["errors"].append("Langfuse public key is required when using Langfuse provider")
                validation_result["valid"] = False
            if not self.settings.langfuse_secret_key:
                validation_result["errors"].append("Langfuse secret key is required when using Langfuse provider")
                validation_result["valid"] = False
            if not self.settings.langfuse_host:
                validation_result["errors"].append("Langfuse host is required when using Langfuse provider")
                validation_result["valid"] = False
        
        # Check repository configuration
        if not self.config.repository.url:
            validation_result["errors"].append("Repository URL is required")
            validation_result["valid"] = False
        
        # Check output directory
        reports_dir = Path(self.config.reports.output_dir)
        if not reports_dir.exists():
            try:
                reports_dir.mkdir(parents=True, exist_ok=True)
                validation_result["warnings"].append(f"Created reports directory: {reports_dir}")
            except Exception as e:
                validation_result["errors"].append(f"Cannot create reports directory: {e}")
                validation_result["valid"] = False
        
        return validation_result


# Global configuration instance
config_manager = ConfigManager()
