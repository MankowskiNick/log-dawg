"""
JSON response parser for Stage 2 - Enhanced for two-stage processing
"""
import json
import re
from typing import Dict, Any, List, Optional
from src.core.logging import get_logger
from src.models.schemas import DiagnosisResult, ParsedLogEntry, ContextDiscoveryResult
from .base import BaseResponseParser


class JsonResponseParser(BaseResponseParser):
    """Enhanced parser for Stage 2 JSON-structured LLM responses"""
    
    def __init__(self):
        self.logger = get_logger("json_parser")
    
    def parse_response(
        self, 
        response_text: str, 
        parsed_log: ParsedLogEntry,
        context_discovery_result: Optional[ContextDiscoveryResult] = None
    ) -> DiagnosisResult:
        """Parse JSON-structured LLM response"""
        
        relevant_code_files = []
        
        # FIRST PRIORITY: Filter context-discovered files to only include those with snippets
        if context_discovery_result and context_discovery_result.files_analyzed:
            self.logger.info(f"Context discovery found {len(context_discovery_result.files_analyzed)} files")
            
            # Filter to only include files that have snippets
            files_with_snippets = [
                file_info for file_info in context_discovery_result.files_analyzed
                if file_info.snippets and len(file_info.snippets) > 0
            ]
            
            files_without_snippets = [
                file_info for file_info in context_discovery_result.files_analyzed
                if not file_info.snippets or len(file_info.snippets) == 0
            ]
            
            # Only include files with snippets in the final result
            relevant_code_files = files_with_snippets
            
            self.logger.info(f"Filtered to {len(files_with_snippets)} files with snippets, excluded {len(files_without_snippets)} files without snippets")
            
            # Log details of filtered files for debugging
            if files_without_snippets:
                filtered_file_paths = [f.file_path for f in files_without_snippets]
                self.logger.debug(f"Files excluded (no snippets): {filtered_file_paths}")
        else:
            self.logger.warning("No context discovery result or files found")
        
        try:
            json_data = json.loads(response_text.strip())
            self.logger.info("Successfully parsed LLM response as JSON")
            return self._parse_json_data(json_data, parsed_log, context_discovery_result, relevant_code_files)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            return self._create_fallback_diagnosis(parsed_log, f"JSON parsing error: {e}")
    
    def _parse_json_data(
        self,
        json_data: Dict[str, Any],
        parsed_log: ParsedLogEntry,
        context_discovery_result: Optional[ContextDiscoveryResult] = None,
        relevant_code_files: List = None
    ) -> DiagnosisResult:
        """Parse JSON data into DiagnosisResult"""
        
        if relevant_code_files is None:
            relevant_code_files = []
        
        # Extract fields directly from JSON with validation
        title = json_data.get("title", "Error Analysis")
        if len(title) > 60:
            title = title[:57] + "..."
        
        error_type = self._extract_error_type(json_data, parsed_log)
        summary = json_data.get("summary", "Log analysis completed")
        root_cause = json_data.get("root_cause", "Root cause analysis pending")
        error_analysis = json_data.get("error_analysis", "Detailed error analysis pending")
        
        # Handle recommendations (should be array)
        recommendations = json_data.get("recommendations", [])
        if not isinstance(recommendations, list):
            recommendations = ["Review error logs", "Check recent code changes"]
        elif not recommendations:
            recommendations = ["Review error logs", "Check recent code changes"]
        
        # Handle confidence score (should be float between 0.0 and 1.0)
        confidence_score = json_data.get("confidence_score", 0.5)
        if not isinstance(confidence_score, (int, float)):
            confidence_score = 0.5
        confidence_score = max(0.0, min(1.0, float(confidence_score)))
        
        # Handle relevant_code_files from JSON (these are just file paths)
        json_file_paths = json_data.get("relevant_code_files", [])
        if isinstance(json_file_paths, list) and context_discovery_result:
            # Try to match JSON file paths with context-discovered files
            analyzed_files_map = {
                file.file_path: file 
                for file in context_discovery_result.files_analyzed
            }
            existing_paths = {
                file.file_path
                for file in relevant_code_files
            }
            
            for path in json_file_paths:
                if isinstance(path, str) and path in analyzed_files_map and path not in existing_paths:
                    relevant_code_files.append(analyzed_files_map[path])
        
        # Log the final files for debugging
        self.logger.info(f"JSON parsing result contains {len(relevant_code_files)} relevant code files")
        for i, file_info in enumerate(relevant_code_files[:3]):  # Log first 3 for debugging
            file_path = file_info.file_path if hasattr(file_info, 'file_path') else str(file_info)
            snippets_count = len(file_info.snippets) if hasattr(file_info, 'snippets') else 0
            self.logger.debug(f"File {i}: {file_path} with {snippets_count} snippets")
        
        return DiagnosisResult(
            title=title,
            error_type=error_type,
            summary=summary,
            root_cause=root_cause,
            error_analysis=error_analysis,
            recommendations=recommendations,
            confidence_score=confidence_score,
            relevant_code_files=relevant_code_files
        )
    
    def parse_response_with_repair(
        self, 
        response_text: str, 
        parsed_log: ParsedLogEntry,
        context_discovery_result: Optional[ContextDiscoveryResult] = None
    ) -> DiagnosisResult:
        """Parse JSON response with automatic repair attempts"""
        
        # First try normal parsing
        try:
            return self.parse_response(response_text, parsed_log, context_discovery_result)
        except Exception as e:
            self.logger.warning(f"Initial JSON parsing failed: {e}, attempting repair")
        
        # Try to repair common JSON issues
        repaired_text = self._repair_json(response_text)
        
        try:
            json_data = json.loads(repaired_text)
            self.logger.info("Successfully parsed repaired JSON")
            
            relevant_code_files = []
            if context_discovery_result and context_discovery_result.files_analyzed:
                # Apply the same filtering logic as in parse_response
                files_with_snippets = [
                    file_info for file_info in context_discovery_result.files_analyzed
                    if file_info.snippets and len(file_info.snippets) > 0
                ]
                relevant_code_files = files_with_snippets
                
                files_without_snippets = len(context_discovery_result.files_analyzed) - len(files_with_snippets)
                if files_without_snippets > 0:
                    self.logger.info(f"Repair path: Filtered to {len(files_with_snippets)} files with snippets, excluded {files_without_snippets} files without snippets")
            
            return self._parse_json_data(json_data, parsed_log, context_discovery_result, relevant_code_files)
        except Exception as e:
            self.logger.error(f"JSON repair also failed: {e}")
            return self._create_fallback_diagnosis(parsed_log, f"JSON parsing and repair failed: {e}")
    
    def _repair_json(self, text: str) -> str:
        """Attempt to repair common JSON formatting issues"""
        
        # Clean up the text
        cleaned = text.strip()
        
        # Remove markdown code blocks if present
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        if cleaned.startswith('```'):
            cleaned = cleaned[3:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        
        cleaned = cleaned.strip()
        
        # Ensure it starts and ends with braces
        if not cleaned.startswith('{'):
            # Try to find the first {
            start_idx = cleaned.find('{')
            if start_idx != -1:
                cleaned = cleaned[start_idx:]
            else:
                # No valid JSON found
                return cleaned
        
        if not cleaned.endswith('}'):
            # Try to find the last }
            end_idx = cleaned.rfind('}')
            if end_idx != -1:
                cleaned = cleaned[:end_idx + 1]
        
        # Fix common JSON issues
        # Remove trailing commas before closing braces/brackets
        cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
        
        # Fix unescaped quotes in strings (basic attempt)
        # This is a simplified approach - more complex cases might need better handling
        cleaned = re.sub(r'(?<!\\)"(?=.*".*:)', r'\\"', cleaned)
        
        return cleaned
    
    def _extract_error_type(self, json_data: Dict[str, Any], parsed_log: ParsedLogEntry) -> str:
        """Extract error type with simple fallback logic"""
        
        # 1. First priority: Use LLM-extracted error type from JSON
        llm_error_type = json_data.get("error_type", "").strip()
        if llm_error_type:
            self.logger.debug(f"Using LLM-extracted error type: {llm_error_type}")
            return llm_error_type
        
        # 2. Second priority: Extract from raw log data if available
        if isinstance(parsed_log.raw_content, dict):
            # Check error_details.error_type
            error_details = parsed_log.raw_content.get("error_details", {})
            if isinstance(error_details, dict):
                raw_error_type = error_details.get("error_type", "").strip()
                if raw_error_type:
                    self.logger.debug(f"Using raw log error type: {raw_error_type}")
                    return raw_error_type
            
            # Check top-level error_type field
            raw_error_type = parsed_log.raw_content.get("error_type", "").strip()
            if raw_error_type:
                self.logger.debug(f"Using top-level raw error type: {raw_error_type}")
                return raw_error_type
        
        # 3. Final fallback: Generic "Error"
        self.logger.debug("Using generic fallback error type: Error")
        return "Error"
    
    def _create_fallback_diagnosis(self, parsed_log: ParsedLogEntry, error: str) -> DiagnosisResult:
        """Create fallback diagnosis when JSON parsing fails"""
        
        # Generate fallback title
        title = f"{parsed_log.level.title()} Level Issue"
        if parsed_log.service_name:
            title = f"{title} in {parsed_log.service_name}"
        
        return DiagnosisResult(
            title=title,
            error_type="Error",
            summary=f"Error log detected: {parsed_log.level} level issue",
            root_cause=f"Analysis failed due to JSON parsing error: {error}",
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
