"""
Markdown report generator for log diagnosis results
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from src.models.schemas import LogDiagnosisResponse, DiagnosisResult, GitInfo, ParsedLogEntry
from src.core.config import config_manager

class MarkdownReportWriter:
    """Generates markdown reports for log diagnosis results"""
    
    def __init__(self):
        self.config = config_manager.config
        self.reports_dir = Path(self.config.reports.output_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_report(
        self, 
        diagnosis_response: LogDiagnosisResponse,
        parsed_log: ParsedLogEntry
    ) -> str:
        """Generate a comprehensive markdown report"""
        
        # Generate filename
        filename = self._generate_filename(diagnosis_response, parsed_log)
        report_path = self.reports_dir / filename
        
        # Generate markdown content
        markdown_content = self._build_markdown_content(diagnosis_response, parsed_log)
        
        # Write markdown to file
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # Save structured data alongside markdown
        self._save_structured_data(filename, diagnosis_response, parsed_log)
        
        # Clean up old reports if needed
        self._cleanup_old_reports()
        
        return str(report_path)
    
    def _generate_filename(self, diagnosis_response: LogDiagnosisResponse, parsed_log: ParsedLogEntry) -> str:
        """Generate filename for the report"""
        timestamp = diagnosis_response.timestamp.strftime("%Y%m%d_%H%M%S")
        
        # Create hash from log content for uniqueness
        log_content = str(parsed_log.raw_content)
        content_hash = hashlib.md5(log_content.encode()).hexdigest()[:8]
        
        # Use configured format or default
        filename_format = self.config.reports.filename_format
        filename = filename_format.format(
            timestamp=timestamp,
            hash=content_hash
        )
        
        return filename
    
    def _build_markdown_content(
        self, 
        diagnosis_response: LogDiagnosisResponse,
        parsed_log: ParsedLogEntry
    ) -> str:
        """Build the complete markdown content"""
        
        sections = []
        
        # Title
        sections.append(f"# Log Diagnosis Report")
        sections.append("")
        sections.append(f"**Generated:** {diagnosis_response.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        sections.append(f"**Diagnosis ID:** `{diagnosis_response.diagnosis_id}`")
        sections.append(f"**Processing Time:** {diagnosis_response.processing_time_seconds:.2f} seconds")
        sections.append("")
        
        # Executive Summary
        sections.append("## Executive Summary")
        sections.append("")
        sections.append(diagnosis_response.diagnosis_result.summary)
        sections.append("")
        
        # Confidence Score
        confidence = diagnosis_response.diagnosis_result.confidence_score
        confidence_bar = self._create_confidence_bar(confidence)
        sections.append(f"**Confidence Score:** {confidence:.1%} {confidence_bar}")
        sections.append("")
        
        # Error Details
        sections.append("## Error Details")
        sections.append("")
        sections.append("### Log Information")
        sections.append("")
        sections.append(f"- **Timestamp:** {parsed_log.timestamp or 'Unknown'}")
        sections.append(f"- **Log Level:** `{parsed_log.level}`")
        sections.append(f"- **Source:** {parsed_log.source or 'Unknown'}")
        sections.append(f"- **Service:** {parsed_log.service_name or 'Unknown'}")
        sections.append("")
        
        # Original Log Message
        sections.append("### Original Log Message")
        sections.append("")
        sections.append("```")
        sections.append(parsed_log.message)
        sections.append("```")
        sections.append("")
        
        # Stack Trace (if available)
        if parsed_log.stack_trace:
            sections.append("### Stack Trace")
            sections.append("")
            sections.append("```")
            sections.append(parsed_log.stack_trace)
            sections.append("```")
            sections.append("")
        
        # Extracted Error Patterns
        if parsed_log.extracted_errors:
            sections.append("### Extracted Error Patterns")
            sections.append("")
            for i, error in enumerate(parsed_log.extracted_errors, 1):
                sections.append(f"{i}. `{error}`")
            sections.append("")
        
        # Root Cause Analysis
        sections.append("## Root Cause Analysis")
        sections.append("")
        sections.append(diagnosis_response.diagnosis_result.root_cause)
        sections.append("")
        
        # Technical Analysis
        sections.append("## Technical Analysis")
        sections.append("")
        sections.append(diagnosis_response.diagnosis_result.error_analysis)
        sections.append("")
        
        # Repository Context
        sections.append("## Repository Context")
        sections.append("")
        git_info = diagnosis_response.git_info
        sections.append(f"- **Branch:** `{git_info.branch}`")
        sections.append(f"- **Current Commit:** `{git_info.current_commit[:12]}`")
        sections.append(f"- **Last Pull:** {git_info.last_pull_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        sections.append("")
        
        # Recent Commits
        if git_info.recent_commits:
            sections.append("### Recent Commits")
            sections.append("")
            for commit in git_info.recent_commits[:5]:  # Show top 5
                sections.append(f"#### {commit['short_hash']} - {commit['message']}")
                sections.append(f"**Author:** {commit['author']} | **Date:** {commit['date']}")
                
                if commit['changed_files']:
                    sections.append("**Changed Files:**")
                    for file_path in commit['changed_files'][:10]:  # Limit to 10 files
                        sections.append(f"- `{file_path}`")
                sections.append("")
        
        # Recently Changed Files
        if git_info.changed_files:
            sections.append("### Recently Changed Files")
            sections.append("")
            for file_path in git_info.changed_files[:20]:  # Show up to 20 files
                sections.append(f"- `{file_path}`")
            sections.append("")
        
        # Relevant Code Files
        if diagnosis_response.diagnosis_result.relevant_code_files:
            sections.append("## Relevant Code Files")
            sections.append("")
            sections.append("The following files are most likely related to this error:")
            sections.append("")
            
            for file_item in diagnosis_response.diagnosis_result.relevant_code_files:
                # Handle both string and dict formats
                if isinstance(file_item, dict):
                    file_path = file_item.get('file_path', str(file_item))
                    size_kb = file_item.get('size_kb')
                    selection_reason = file_item.get('selection_reason')
                    snippets = file_item.get('snippets', [])
                    
                    # Display file with size and reason if available
                    if size_kb and selection_reason:
                        sections.append(f"- `{file_path}` ({size_kb:.1f}KB) - {selection_reason}")
                    elif size_kb:
                        sections.append(f"- `{file_path}` ({size_kb:.1f}KB)")
                    elif selection_reason:
                        sections.append(f"- `{file_path}` - {selection_reason}")
                    else:
                        sections.append(f"- `{file_path}`")
                    
                    # Include snippets if available
                    if snippets and len(snippets) > 0:
                        sections.append(f"  - {len(snippets)} relevant code snippet(s) identified")
                        
                elif isinstance(file_item, str):
                    sections.append(f"- `{file_item}`")
                else:
                    # Handle FileContentInfo objects directly
                    sections.append(f"- `{file_item.file_path}`")
            
            sections.append("")
        
        # Recommendations
        sections.append("## Recommendations")
        sections.append("")
        
        # Group and format recommendations properly
        recommendations = self._format_recommendations(diagnosis_response.diagnosis_result.recommendations)
        
        for i, recommendation in enumerate(recommendations, 1):
            sections.append(f"### {i}. {recommendation['title']}")
            sections.append("")
            if recommendation['content']:
                sections.extend(recommendation['content'])
                sections.append("")
        
        # Action Items
        sections.append("## Action Items")
        sections.append("")
        sections.append("- [ ] Review the root cause analysis")
        sections.append("- [ ] Implement immediate fixes")
        sections.append("- [ ] Review relevant code files")
        sections.append("- [ ] Update monitoring/alerts if needed")
        sections.append("- [ ] Document lessons learned")
        sections.append("")
        
        # Metadata
        sections.append("---")
        sections.append("")
        sections.append("## Report Metadata")
        sections.append("")
        sections.append(f"- **Report File:** `{diagnosis_response.report_file_path}`")
        sections.append(f"- **Diagnosis ID:** `{diagnosis_response.diagnosis_id}`")
        sections.append(f"- **Log Dawg Version:** {self._get_version()}")
        sections.append(f"- **Generated At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        return "\n".join(sections)
    
    def _create_confidence_bar(self, confidence: float) -> str:
        """Create a visual confidence bar"""
        filled_blocks = int(confidence * 10)
        empty_blocks = 10 - filled_blocks
        
        filled = "█" * filled_blocks
        empty = "░" * empty_blocks
        
        return f"[{filled}{empty}]"
    
    def _format_recommendations(self, recommendations: list) -> list:
        """Format and group recommendations properly"""
        if not recommendations:
            return []
        
        formatted_recommendations = []
        
        # Join all recommendations into a single text block for processing
        full_text = "\n".join(recommendations)
        
        # Split by common recommendation indicators
        import re
        
        # Look for patterns like ". **Fix" or numbered items starting with digits
        # But be more careful about the regex pattern
        sections = re.split(r'(?=\d*\.\s*\*?\*?[A-Z][^:]*:)', full_text)
        
        # If no clear sections found, treat each major chunk as a recommendation
        if len(sections) <= 1:
            # Try splitting on numbered recommendations differently
            sections = re.split(r'(?=\d+\.\s*[A-Z])', full_text)
        
        # If still no sections, fallback to simple grouping
        if len(sections) <= 1:
            # Group recommendations based on content structure
            current_group = []
            current_title = ""
            
            for item in recommendations:
                item = item.strip()
                if not item:
                    continue
                
                # Check if this looks like a title (starts with number/bullet and has colon or **bold**)
                if (re.match(r'^\d*\.\s*\*?\*?[A-Z].*[:\*]', item) or 
                    item.startswith('. **') or 
                    (len(item) < 50 and ':' in item)):
                    
                    # Save previous group if it exists
                    if current_title and current_group:
                        formatted_recommendations.append({
                            "title": current_title,
                            "content": current_group
                        })
                    
                    # Start new group
                    current_title = re.sub(r'^\d*\.\s*\*?\*?', '', item)
                    current_title = re.sub(r'\*?\*?:?\s*$', '', current_title).strip()
                    current_group = []
                
                else:
                    # Add to current group
                    current_group.append(item)
            
            # Add final group
            if current_title and current_group:
                formatted_recommendations.append({
                    "title": current_title,
                    "content": current_group
                })
            
            # If we still have no recommendations, add the remaining items as a single recommendation
            if not formatted_recommendations and recommendations:
                formatted_recommendations.append({
                    "title": "Implementation Steps",
                    "content": recommendations
                })
        
        else:
            # Process the sections we found
            for i, section in enumerate(sections):
                section = section.strip()
                if not section:
                    continue
                
                lines = [line.strip() for line in section.split('\n') if line.strip()]
                if not lines:
                    continue
                
                # Extract title from first line
                first_line = lines[0]
                
                # Clean up numbering and formatting from title
                title = re.sub(r'^\d*\.\s*', '', first_line)  # Remove "1. "
                title = re.sub(r'^\*?\*?', '', title)  # Remove bold markers
                title = re.sub(r'\*?\*?:?\s*$', '', title)  # Remove trailing markers
                title = title.strip()
                
                if not title or len(title) < 3:
                    title = f"Recommendation {i + 1}"
                
                # Process content lines and handle code blocks
                content_lines = []
                code_block = []
                in_code = False
                
                # Join lines that might be part of the same logical unit
                processed_lines = []
                i = 0
                while i < len(lines[1:]):  # Skip the title line
                    line = lines[i + 1]  # +1 because we're skipping the title
                    if not line:
                        i += 1
                        continue
                    
                    # Check if this line and the next should be joined (like broken printf statements)
                    if (i + 2 < len(lines) and 
                        line.endswith('"') == False and 
                        'printf(' in line and
                        lines[i + 2].startswith('", ')):
                        # Join broken printf statement
                        next_line = lines[i + 2]
                        joined_line = line + '\\n' + next_line
                        processed_lines.append(joined_line)
                        i += 2  # Skip the next line since we've joined it
                    else:
                        processed_lines.append(line)
                        i += 1
                
                # Now process the cleaned lines
                for line in processed_lines:
                    if not line:
                        continue
                    
                    # Detect code patterns - be more specific about shell vs C
                    is_c_code = (
                        line.startswith(('//','if (','for (','printf(','```')) or
                        line.endswith(('{',';')) or
                        re.match(r'^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*\(', line)  # function calls
                    )
                    
                    is_shell_code = (
                        line.startswith('#') and not line.startswith('# Example') or
                        line.startswith('for ') and 'in ' in line and line.endswith(' do') or
                        line.startswith(('echo ', 'cat ', 'ls ', 'cd ', 'if [', 'exit ', 'fi', 'done')) or
                        line.strip() in ['fi', 'done'] or
                        ('$' in line and any(cmd in line for cmd in ['echo', 'exit']))
                    )
                    
                    is_code_line = is_c_code or is_shell_code
                    
                    if is_code_line and not in_code:
                        # Start appropriate code block
                        in_code = True
                        if is_shell_code:
                            content_lines.append("```bash")
                        else:
                            content_lines.append("```c")
                        code_block = [line]
                    elif is_code_line and in_code:
                        # Continue code block
                        code_block.append(line)
                    elif not is_code_line and in_code:
                        # End code block
                        content_lines.extend(code_block)
                        content_lines.append("```")
                        content_lines.append("")
                        content_lines.append(line)
                        in_code = False
                        code_block = []
                    else:
                        # Regular text
                        content_lines.append(line)
                
                # Close any open code block
                if in_code and code_block:
                    content_lines.extend(code_block)
                    content_lines.append("```")
                
                formatted_recommendations.append({
                    "title": title,
                    "content": content_lines
                })
        
        # Ensure we have at least one recommendation
        if not formatted_recommendations:
            formatted_recommendations = [{
                "title": "Review Error Analysis",
                "content": [
                    "Based on the diagnosis above:",
                    "",
                    "- Review the root cause analysis",
                    "- Check the identified code files", 
                    "- Implement suggested fixes",
                    "- Monitor for similar issues"
                ]
            }]
        
        return formatted_recommendations

    def _get_version(self) -> str:
        """Get the current version of Log Dawg"""
        try:
            from src import __version__
            return __version__
        except ImportError:
            return "Unknown"
    
    def _cleanup_old_reports(self):
        """Clean up old reports if exceeding max limit"""
        max_reports = self.config.reports.max_reports
        
        if max_reports <= 0:
            return
        
        # Get all report files sorted by modification time
        report_files = []
        for file_path in self.reports_dir.glob("*.md"):
            if file_path.is_file():
                report_files.append((file_path.stat().st_mtime, file_path))
        
        # Sort by modification time (newest first)
        report_files.sort(reverse=True)
        
        # Remove excess files
        if len(report_files) > max_reports:
            files_to_remove = report_files[max_reports:]
            for _, file_path in files_to_remove:
                try:
                    file_path.unlink()
                    print(f"Removed old report: {file_path.name}")
                except Exception as e:
                    print(f"Failed to remove old report {file_path.name}: {e}")
    
    def list_reports(self, limit: int = 20) -> list:
        """List recent reports with enhanced metadata"""
        report_files = []
        
        for file_path in self.reports_dir.glob("*.md"):
            if file_path.is_file():
                stat = file_path.stat()
                
                # Get structured data for enhanced display
                structured_data = self.get_structured_data(file_path.name)
                
                # Generate display title and metadata
                display_info = self._generate_display_info(file_path.name, structured_data)
                
                report_info = {
                    "filename": file_path.name,
                    "path": str(file_path),
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime),
                    "created": datetime.fromtimestamp(stat.st_ctime),
                    "display_title": display_info["title"],
                    "error_type": display_info["error_type"], 
                    "confidence_score": display_info["confidence_score"],
                    "processing_time": display_info["processing_time"],
                    "summary_preview": display_info["summary_preview"]
                }
                
                # Add diagnosis_id from structured data if available
                if structured_data:
                    report_info["diagnosis_id"] = structured_data.get("diagnosis_id")
                
                report_files.append(report_info)
        
        # Sort by modification time (newest first)
        report_files.sort(key=lambda x: x["modified"], reverse=True)
        
        return report_files[:limit]
    
    def _generate_display_info(self, filename: str, structured_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate display-friendly information from structured data"""
        import re
        
        # Default fallback values
        display_info = {
            "title": filename.replace('.md', '').replace('_', ' ').title(),
            "error_type": "Unknown Error",
            "confidence_score": 0.0,
            "processing_time": 0.0,
            "summary_preview": "No summary available"
        }
        
        if not structured_data:
            return display_info
        
        # Extract confidence score and processing time
        diagnosis_result = structured_data.get('diagnosis_result', {})
        display_info['confidence_score'] = diagnosis_result.get('confidence_score', 0.0)
        display_info['processing_time'] = structured_data.get('processing_time_seconds', 0.0)
        
        # Use title from diagnosis result if available, otherwise extract from summary
        title = diagnosis_result.get('title', '')
        if title:
            display_info['title'] = title
        else:
            # Fallback: try to extract a meaningful title from the summary
            summary = diagnosis_result.get('summary', '')
            if summary:
                title = self._extract_title_from_summary(summary)
                if title:
                    display_info['title'] = title
        
        # Generate a short preview (first 2 sentences) from summary
        summary = diagnosis_result.get('summary', '')
        if summary:
            preview = self._generate_summary_preview(summary)
            display_info['summary_preview'] = preview
        
        # Extract error type from various sources
        error_type = self._extract_error_type(structured_data)
        if error_type:
            display_info['error_type'] = error_type
        
        return display_info
    
    def _extract_title_from_summary(self, summary: str) -> Optional[str]:
        """Extract a meaningful title from the summary text"""
        import re
        
        # Clean up the summary
        summary = summary.strip()
        if not summary:
            return None
        
        # Try to extract key information to create a concise title
        summary_lower = summary.lower()
        
        # Pattern-based title generation for common error types
        if 'shader' in summary_lower and 'compil' in summary_lower:
            if 'vertex' in summary_lower:
                return "Vertex Shader Compilation Failure"
            elif 'fragment' in summary_lower:
                return "Fragment Shader Compilation Failure"
            else:
                return "Shader Compilation Error"
        
        if 'segmentation fault' in summary_lower or 'segfault' in summary_lower:
            return "Segmentation Fault Error"
        
        if 'memory leak' in summary_lower:
            return "Memory Leak Detected"
        
        if 'null pointer' in summary_lower:
            return "Null Pointer Dereference"
        
        if 'file not found' in summary_lower or 'cannot open file' in summary_lower:
            return "File Access Error"
        
        if 'connection timeout' in summary_lower:
            return "Connection Timeout"
        
        if 'out of memory' in summary_lower:
            return "Memory Exhaustion"
        
        if 'buffer overflow' in summary_lower:
            return "Buffer Overflow"
        
        if 'stack overflow' in summary_lower:
            return "Stack Overflow"
        
        # Look for specific error descriptions in the text
        error_patterns = {
            r'failed to (open|read|load|compile|initialize) (.+?)(?:\s|,|\.|$)': lambda m: f"Failed to {m.group(1).title()} {m.group(2).title()}",
            r'cannot (open|read|load|find|access) (.+?)(?:\s|,|\.|$)': lambda m: f"Cannot {m.group(1).title()} {m.group(2).title()}",
            r'missing (.+?)(?:\s|,|\.|$)': lambda m: f"Missing {m.group(1).title()}",
            r'invalid (.+?)(?:\s|,|\.|$)': lambda m: f"Invalid {m.group(1).title()}",
            r'corrupt(ed)? (.+?)(?:\s|,|\.|$)': lambda m: f"Corrupted {m.group(2).title()}",
        }
        
        for pattern, title_func in error_patterns.items():
            match = re.search(pattern, summary_lower)
            if match:
                title = title_func(match)
                if len(title) <= 60:  # Keep it concise
                    return title
        
        # Extract the main action/problem from the first sentence
        sentences = re.split(r'[.!?]+', summary)
        first_sentence = sentences[0].strip() if sentences else summary
        
        # Clean up the first sentence to make it more title-like
        first_sentence = re.sub(r'^(the\s+)?error\s+(occurs|arises|is)', 'Error', first_sentence, flags=re.IGNORECASE)
        first_sentence = re.sub(r'^(the\s+)?log\s+(indicates|shows)', 'Log Analysis:', first_sentence, flags=re.IGNORECASE)
        first_sentence = re.sub(r'^(the\s+)?issue\s+(is|occurs)', 'Issue:', first_sentence, flags=re.IGNORECASE)
        
        # Remove unnecessary words
        first_sentence = re.sub(r'\s+(during|within|in\s+the)\s+', ' ', first_sentence, flags=re.IGNORECASE)
        first_sentence = re.sub(r'\s+specifically\s+', ' ', first_sentence, flags=re.IGNORECASE)
        
        # Limit length and clean up
        if len(first_sentence) > 60:
            # Try to cut at a natural break point
            words = first_sentence.split()
            truncated = []
            length = 0
            for word in words:
                if length + len(word) + 1 > 57:  # Leave room for "..."
                    break
                truncated.append(word)
                length += len(word) + 1
            first_sentence = ' '.join(truncated) + "..."
        
        return first_sentence if first_sentence else None
    
    def _generate_summary_preview(self, summary: str) -> str:
        """Generate a short preview from the summary"""
        import re
        
        # Get first 2 sentences
        sentences = re.split(r'[.!?]+', summary.strip())
        preview_sentences = []
        
        for sentence in sentences[:2]:
            sentence = sentence.strip()
            if sentence:
                preview_sentences.append(sentence)
        
        preview = '. '.join(preview_sentences)
        if preview and not preview.endswith('.'):
            preview += '.'
        
        # Limit length
        if len(preview) > 200:
            preview = preview[:197] + "..."
        
        return preview if preview else "No preview available"
    
    def _extract_error_type(self, structured_data: Dict[str, Any]) -> Optional[str]:
        """Extract error type from structured data"""
        # Use LLM-generated error type from structured data
        diagnosis_result = structured_data.get('diagnosis_result', {})
        return diagnosis_result.get('error_type')
    
    def get_report_content(self, filename: str) -> Optional[str]:
        """Get content of a specific report"""
        report_path = self.reports_dir / filename
        
        if not report_path.exists():
            return None
        
        try:
            return report_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Error reading report {filename}: {e}")
            return None
    
    def _save_structured_data(
        self, 
        filename: str, 
        diagnosis_response: LogDiagnosisResponse, 
        parsed_log: ParsedLogEntry
    ):
        """Save structured data alongside markdown report"""
        # Create JSON filename (same as markdown but with .json extension)
        json_filename = filename.replace('.md', '.json')
        json_path = self.reports_dir / json_filename
        
        # Convert to serializable format
        structured_data = {
            "diagnosis_id": diagnosis_response.diagnosis_id,
            "timestamp": diagnosis_response.timestamp.isoformat(),
            "processing_time_seconds": diagnosis_response.processing_time_seconds,
            "diagnosis_result": {
                "title": getattr(diagnosis_response.diagnosis_result, 'title', 'Error Analysis'),
                "error_type": getattr(diagnosis_response.diagnosis_result, 'error_type', 'Runtime Error'),
                "summary": diagnosis_response.diagnosis_result.summary,
                "root_cause": diagnosis_response.diagnosis_result.root_cause,
                "error_analysis": diagnosis_response.diagnosis_result.error_analysis,
                "recommendations": diagnosis_response.diagnosis_result.recommendations,
                "confidence_score": diagnosis_response.diagnosis_result.confidence_score,
                "relevant_code_files": [
                    {
                        "file_path": f.file_path,
                        "size_kb": f.size_kb,
                        "snippets": [
                            {
                                "start_line": snippet.start_line,
                                "end_line": snippet.end_line,
                                "content": snippet.content
                            }
                            for snippet in (f.snippets or [])
                        ],
                        "relevance_score": f.relevance_score,
                        "selection_reason": f.selection_reason
                    }
                    for f in (diagnosis_response.diagnosis_result.relevant_code_files or [])
                ]
            },
            "git_info": {
                "branch": diagnosis_response.git_info.branch,
                "current_commit": diagnosis_response.git_info.current_commit,
                "last_pull_time": diagnosis_response.git_info.last_pull_time.isoformat(),
                "recent_commits": diagnosis_response.git_info.recent_commits,
                "changed_files": diagnosis_response.git_info.changed_files
            },
            "parsed_log": {
                "timestamp": parsed_log.timestamp,
                "level": parsed_log.level,
                "message": parsed_log.message,
                "source": parsed_log.source,
                "service_name": parsed_log.service_name,
                "stack_trace": parsed_log.stack_trace,
                "extracted_errors": parsed_log.extracted_errors
            }
        }
        
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Failed to save structured data for {filename}: {e}")
    
    def get_structured_data(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get structured data for a specific report"""
        json_filename = filename.replace('.md', '.json')
        json_path = self.reports_dir / json_filename
        
        if not json_path.exists():
            return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error reading structured data for {filename}: Invalid JSON - {e}")
            return None
        except Exception as e:
            print(f"Error reading structured data for {filename}: {e}")
            return None
    
    def get_report_with_data(self, filename: str) -> Optional[Dict[str, Any]]:
        """Get both markdown content and structured data for a report"""
        markdown_content = self.get_report_content(filename)
        structured_data = self.get_structured_data(filename)
        
        if markdown_content is None:
            return None
        
        return {
            "filename": filename,
            "content": markdown_content,
            "structured_data": structured_data,
            "timestamp": datetime.now().isoformat()
        }

    def get_report_stats(self) -> Dict[str, Any]:
        """Get statistics about reports"""
        report_files = list(self.reports_dir.glob("*.md"))
        
        if not report_files:
            return {
                "total_reports": 0,
                "total_size_mb": 0,
                "oldest_report": None,
                "newest_report": None,
                "reports_today": 0,
                "average_confidence_score": 0
            }
        
        total_size = sum(f.stat().st_size for f in report_files)
        modification_times = [f.stat().st_mtime for f in report_files]
        
        # Calculate reports today and average confidence
        today = datetime.now().date()
        reports_today = 0
        confidence_scores = []
        
        for report_file in report_files:
            # Check if report was created today
            file_date = datetime.fromtimestamp(report_file.stat().st_ctime).date()
            if file_date == today:
                reports_today += 1
            
            # Try to get confidence score from structured data
            structured_data = self.get_structured_data(report_file.name)
            if structured_data and structured_data.get('diagnosis_result', {}).get('confidence_score'):
                confidence_scores.append(structured_data['diagnosis_result']['confidence_score'])
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        return {
            "total_reports": len(report_files),
            "total_size_mb": total_size / (1024 * 1024),
            "oldest_report": datetime.fromtimestamp(min(modification_times)),
            "newest_report": datetime.fromtimestamp(max(modification_times)),
            "reports_today": reports_today,
            "average_confidence_score": round(avg_confidence * 100, 1)  # Convert to percentage
        }
