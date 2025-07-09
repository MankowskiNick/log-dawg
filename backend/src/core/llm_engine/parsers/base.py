"""
Base response parser interface
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from src.models.schemas import DiagnosisResult, ParsedLogEntry, ContextDiscoveryResult


class BaseResponseParser(ABC):
    """Abstract base class for response parsers"""
    
    @abstractmethod
    def parse_response(
        self, 
        response_text: str, 
        parsed_log: ParsedLogEntry,
        context_discovery_result: Optional[ContextDiscoveryResult] = None
    ) -> DiagnosisResult:
        """Parse LLM response into structured DiagnosisResult"""
        pass
    
    def _create_fallback_diagnosis(self, parsed_log: ParsedLogEntry, error: str) -> DiagnosisResult:
        """Create fallback diagnosis when parsing fails"""
        # Generate fallback title
        title = f"{parsed_log.level.title()} Level Issue"
        if parsed_log.service_name:
            title = f"{title} in {parsed_log.service_name}"
        
        return DiagnosisResult(
            title=title,
            error_type="Runtime Error",
            summary=f"Error log detected: {parsed_log.level} level issue",
            root_cause=f"Analysis failed due to parsing error: {error}",
            error_analysis=f"Log contains {len(parsed_log.extracted_errors)} error patterns. Stack trace {'available' if parsed_log.stack_trace else 'not available'}.",
            recommendations=[
                "Review the error log manually",
                "Check recent code changes",
                "Verify system configuration",
                "Monitor for similar errors"
            ],
            confidence_score=0.1,
            relevant_code_files=[]
        )
    
    def _extract_confidence_score(self, text: str) -> float:
        """Extract confidence score from text"""
        import re
        
        # Look for decimal numbers between 0 and 1
        matches = re.findall(r'0?\.\d+', text)
        for match in matches:
            score = float(match)
            if 0.0 <= score <= 1.0:
                return score
        
        # Look for percentages
        matches = re.findall(r'(\d+)%', text)
        for match in matches:
            score = float(match) / 100.0
            if 0.0 <= score <= 1.0:
                return score
        
        # Look for words indicating confidence
        if any(word in text.lower() for word in ['high', 'confident', 'certain']):
            return 0.8
        elif any(word in text.lower() for word in ['medium', 'moderate']):
            return 0.6
        elif any(word in text.lower() for word in ['low', 'uncertain', 'unsure']):
            return 0.3
        
        return 0.5  # Default
    
    def _extract_file_list(self, text: str) -> List[str]:
        """Extract file paths from text"""
        files = []
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Remove list markers
            if line.startswith(('1.', '2.', '3.', '4.', '5.', '-', '*', '•')):
                import re
                clean_line = re.sub(r'^[\d\.\-\*\•]\s*', '', line).strip()
                line = clean_line
            
            # Look for file-like patterns
            if '.' in line and ('/' in line or '\\' in line or line.endswith(('.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.php', '.rb'))):
                files.append(line)
        
        return files[:20]  # Limit to 20 files
