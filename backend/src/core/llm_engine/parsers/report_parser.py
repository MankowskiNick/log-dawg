"""
Report response parser for Stage 1 - Natural language report parsing
"""
from typing import Dict, Any, Optional
from src.core.logging import get_logger
from src.models.schemas import ParsedLogEntry
from .base import BaseResponseParser


class ReportResponseParser(BaseResponseParser):
    """Parser for Stage 1 narrative report responses"""
    
    def __init__(self):
        self.logger = get_logger("report_parser")
    
    def parse_response(
        self, 
        response_text: str, 
        parsed_log: ParsedLogEntry,
        context_discovery_result: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Parse narrative report response into structured intermediate report"""
        
        # Clean up the response text
        cleaned_text = response_text.strip()
        
        # Basic validation
        if not cleaned_text:
            self.logger.error("Empty response received from LLM")
            return self._create_fallback_report(parsed_log, "Empty response from LLM")
        
        if len(cleaned_text) < 100:
            self.logger.warning(f"Very short response received: {len(cleaned_text)} characters")
        
        # Analyze report quality
        quality_metrics = self._analyze_report_quality(cleaned_text)
        
        # Extract key findings
        key_findings = self._extract_key_findings(cleaned_text)
        
        # Estimate confidence based on content analysis
        confidence_score = self._estimate_confidence(cleaned_text, quality_metrics)
        
        self.logger.info(f"Parsed narrative report: {len(cleaned_text)} chars, quality score: {quality_metrics['overall_score']:.2f}")
        
        return {
            "content": cleaned_text,
            "analysis_quality_score": quality_metrics["overall_score"],
            "key_findings": key_findings,
            "stage1_metadata": {
                "response_length": len(cleaned_text),
                "quality_metrics": quality_metrics,
                "confidence_score": confidence_score,
                "has_code_references": quality_metrics["has_code_references"],
                "has_recommendations": quality_metrics["has_recommendations"],
                "structure_score": quality_metrics["structure_score"]
            }
        }
    
    def _analyze_report_quality(self, report_text: str) -> Dict[str, Any]:
        """Analyze the quality of the narrative report"""
        
        # Convert to lowercase for analysis
        text_lower = report_text.lower()
        
        # Check for key sections
        has_summary = any(keyword in text_lower for keyword in [
            "summary", "overview", "executive", "brief"
        ])
        
        has_root_cause = any(keyword in text_lower for keyword in [
            "root cause", "cause", "reason", "origin"
        ])
        
        has_technical_analysis = any(keyword in text_lower for keyword in [
            "technical", "analysis", "stack trace", "error pattern"
        ])
        
        has_recommendations = any(keyword in text_lower for keyword in [
            "recommend", "suggest", "fix", "solution", "action"
        ])
        
        has_code_references = any(keyword in report_text for keyword in [
            ".py", ".js", ".java", ".cs", ".cpp", ".c", ".go", ".rs",
            "line ", "function", "method", "class", "variable"
        ])
        
        has_file_references = "/" in report_text or "\\" in report_text
        
        # Structure analysis
        section_count = report_text.count("#") + report_text.count("##") + report_text.count("###")
        bullet_points = report_text.count("- ") + report_text.count("* ")
        
        # Calculate scores
        content_score = (
            (1 if has_summary else 0) +
            (1 if has_root_cause else 0) +
            (1 if has_technical_analysis else 0) +
            (1 if has_recommendations else 0)
        ) / 4.0
        
        technical_score = (
            (1 if has_code_references else 0) +
            (1 if has_file_references else 0)
        ) / 2.0
        
        structure_score = min(1.0, (section_count + bullet_points) / 10.0)
        
        overall_score = (content_score * 0.5 + technical_score * 0.3 + structure_score * 0.2)
        
        return {
            "overall_score": overall_score,
            "content_score": content_score,
            "technical_score": technical_score,
            "structure_score": structure_score,
            "has_summary": has_summary,
            "has_root_cause": has_root_cause,
            "has_technical_analysis": has_technical_analysis,
            "has_recommendations": has_recommendations,
            "has_code_references": has_code_references,
            "has_file_references": has_file_references,
            "section_count": section_count,
            "bullet_points": bullet_points,
            "word_count": len(report_text.split())
        }
    
    def _extract_key_findings(self, report_text: str) -> list:
        """Extract key findings from the narrative report"""
        
        findings = []
        
        # Look for explicit findings or conclusions
        lines = report_text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and headers
            if not line or line.startswith('#'):
                continue
            
            # Look for bullet points that might be key findings
            if line.startswith('- ') or line.startswith('* '):
                finding = line[2:].strip()
                if len(finding) > 20 and any(keyword in finding.lower() for keyword in [
                    'error', 'issue', 'problem', 'cause', 'recommend', 'fix', 'solution'
                ]):
                    findings.append(finding)
            
            # Look for sentences that contain key information
            elif any(keyword in line.lower() for keyword in [
                'the error is caused by', 'root cause', 'the issue stems from',
                'this error occurs when', 'the problem is'
            ]):
                findings.append(line)
        
        # Limit to most relevant findings
        return findings[:10]
    
    def _estimate_confidence(self, report_text: str, quality_metrics: Dict[str, Any]) -> float:
        """Estimate confidence level based on report content"""
        
        text_lower = report_text.lower()
        
        # Confidence indicators
        high_confidence_indicators = [
            'clearly', 'definitely', 'certainly', 'obviously', 'evident',
            'confirmed', 'verified', 'established'
        ]
        
        low_confidence_indicators = [
            'possibly', 'might', 'could be', 'appears to', 'seems',
            'likely', 'probably', 'potentially', 'unclear', 'uncertain'
        ]
        
        # Count indicators
        high_confidence_count = sum(1 for indicator in high_confidence_indicators if indicator in text_lower)
        low_confidence_count = sum(1 for indicator in low_confidence_indicators if indicator in text_lower)
        
        # Base confidence on quality metrics
        base_confidence = quality_metrics["overall_score"]
        
        # Adjust based on confidence indicators
        confidence_adjustment = (high_confidence_count - low_confidence_count) * 0.05
        
        # Adjust based on technical depth
        if quality_metrics["has_code_references"] and quality_metrics["has_file_references"]:
            confidence_adjustment += 0.1
        
        # Adjust based on completeness
        if quality_metrics["content_score"] > 0.8:
            confidence_adjustment += 0.1
        
        final_confidence = max(0.1, min(1.0, base_confidence + confidence_adjustment))
        
        return final_confidence
    
    def _create_fallback_report(self, parsed_log: ParsedLogEntry, error: str) -> Dict[str, Any]:
        """Create fallback report when parsing fails"""
        
        fallback_content = f"""
# Error Analysis Report

## Executive Summary
Analysis failed due to: {error}

## Error Details
- Log Level: {parsed_log.level}
- Service: {parsed_log.service_name or 'Unknown'}
- Message: {parsed_log.message[:200]}{'...' if len(parsed_log.message) > 200 else ''}

## Recommendations
- Manual review of the error log is required
- Check system logs for additional context
- Verify recent code changes
- Monitor for similar errors

## Confidence Assessment
Low confidence due to analysis failure.
"""
        
        return {
            "content": fallback_content.strip(),
            "analysis_quality_score": 0.1,
            "key_findings": ["Analysis failed - manual review required"],
            "stage1_metadata": {
                "response_length": len(fallback_content),
                "quality_metrics": {
                    "overall_score": 0.1,
                    "content_score": 0.2,
                    "technical_score": 0.0,
                    "structure_score": 0.3,
                    "has_code_references": False,
                    "has_recommendations": True
                },
                "confidence_score": 0.1,
                "is_fallback": True,
                "error": error
            }
        }
