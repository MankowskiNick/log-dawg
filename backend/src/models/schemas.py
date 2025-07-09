"""
Pydantic schemas for API requests and responses
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field

class CodeSnippet(BaseModel):
    """Represents a snippet of code from a file"""
    start_line: int = Field(..., description="Starting line number of the snippet")
    end_line: int = Field(..., description="Ending line number of the snippet")
    content: str = Field(..., description="The actual code snippet content")

class LogData(BaseModel):
    """Schema for incoming log data"""
    content: Union[str, Dict[str, Any]] = Field(..., description="Log content - can be JSON object or plain text")
    source: Optional[str] = Field(None, description="Source of the log (e.g., 'cloudwatch', 'alb')")
    timestamp: Optional[datetime] = Field(None, description="Log timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

class LogDiagnosisRequest(BaseModel):
    """Request schema for log diagnosis"""
    log_data: LogData
    force_git_pull: Optional[bool] = Field(default=True, description="Force git pull before diagnosis")
    include_git_context: Optional[bool] = Field(default=True, description="Include recent git changes in analysis")

class GitInfo(BaseModel):
    """Git repository information"""
    current_commit: str
    branch: str
    recent_commits: List[Dict[str, Any]]
    changed_files: List[str]
    last_pull_time: datetime

class DiagnosisResult(BaseModel):
    """Diagnosis result from LLM"""
    title: str = Field(..., description="Concise, descriptive title for the error (max 60 characters)")
    error_type: str = Field(..., description="Categorized error type (e.g., 'Compilation Error', 'Runtime Error', 'Network Error')")
    summary: str
    root_cause: str
    error_analysis: str
    recommendations: List[str]
    confidence_score: float = Field(ge=0.0, le=1.0)
    relevant_code_files: List['FileContentInfo'] = Field(default_factory=list)
    context_discovery: Optional['ContextDiscoveryResult'] = None

class FileContentInfo(BaseModel):
    """Information about a file's content for context discovery"""
    file_path: str
    size_kb: float
    content: Optional[str] = Field(None, description="The full content of the file, loaded temporarily for processing")
    snippets: List[CodeSnippet] = Field(default_factory=list, description="List of relevant code snippets from the file")
    relevance_score: Optional[float] = None
    selection_reason: Optional[str] = None

    class Config:
        json_encoders = {
            # Ensure proper serialization
            CodeSnippet: lambda v: v.dict() if hasattr(v, 'dict') else v
        }

class ContextDiscoveryRequest(BaseModel):
    """Request for context discovery from LLM"""
    error_message: str
    stack_trace: Optional[str]
    file_structure: str
    current_files: List[str]
    iteration: int
    confidence_history: List[float]

class ContextDiscoveryResponse(BaseModel):
    """Response from LLM for context discovery"""
    requested_files: List[str]
    reasoning: str
    confidence_score: float

class ContextDiscoveryResult(BaseModel):
    """Result from context discovery process"""
    iterations_performed: int
    files_analyzed: List['FileContentInfo']
    confidence_progression: List[float]
    total_context_size_kb: float
    discovery_reasoning: List[str]
    final_confidence: float

class LogDiagnosisQueuedResponse(BaseModel):
    """Response schema for queued log diagnosis request"""
    diagnosis_id: str
    status: str = Field(..., description="Diagnosis status: pending, processing, complete, failed")

class LogDiagnosisStatusResponse(BaseModel):
    """Status/result schema for diagnosis polling"""
    diagnosis_id: str
    status: str = Field(..., description="Diagnosis status: pending, processing, complete, failed")
    diagnosis_result: Optional[DiagnosisResult] = None
    git_info: Optional[GitInfo] = None
    processing_time_seconds: Optional[float] = None
    timestamp: Optional[datetime] = None
    report_file_path: Optional[str] = None
    error: Optional[str] = None

class LogDiagnosisResponse(BaseModel):
    """Response schema for log diagnosis"""
    diagnosis_id: str
    diagnosis_result: DiagnosisResult
    git_info: GitInfo
    processing_time_seconds: float
    timestamp: datetime
    report_file_path: str

class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str
    git_status: Dict[str, Any]
    configuration_valid: bool

class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: datetime

class ParsedLogEntry(BaseModel):
    """Parsed log entry for internal processing"""
    timestamp: Optional[datetime]
    level: str
    message: str
    source: Optional[str]
    stack_trace: Optional[str]
    service_name: Optional[str]
    raw_content: Union[str, Dict[str, Any]]
    extracted_errors: List[str]

class GitCommitInfo(BaseModel):
    """Git commit information"""
    hash: str
    author: str
    date: datetime
    message: str
    changed_files: List[str]
    additions: int
    deletions: int

class IntermediateReport(BaseModel):
    """Intermediate narrative report from Stage 1"""
    content: str = Field(..., description="The full narrative report content")
    analysis_quality_score: float = Field(ge=0.0, le=1.0, description="Quality score of the analysis")
    key_findings: List[str] = Field(default_factory=list, description="Key findings extracted from the report")
    stage1_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata from Stage 1 processing")

class LLMProvider(BaseModel):
    """LLM provider configuration"""
    name: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    max_tokens: int = 2000
    temperature: float = 0.1
