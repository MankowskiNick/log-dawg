"""
Markdown generator for converting JSON reports to markdown format
"""
import re
from datetime import datetime
from typing import Dict, Any, List, Iterator
from pathlib import Path

class MarkdownGenerator:
    """Converts JSON reports to markdown format on-demand"""
    
    def __init__(self):
        pass
    
    def generate_from_json(self, json_report: Dict[str, Any]) -> str:
        """Convert a JSON report to markdown format"""
        
        if not json_report:
            return "# Error\n\nReport data not available."
        
        sections = []
        
        # Extract data from JSON structure
        metadata = json_report.get('metadata', {})
        diagnosis_result = json_report.get('diagnosis_result', {})
        git_info = json_report.get('git_info', {})
        parsed_log = json_report.get('parsed_log', {})
        
        # Title
        sections.append(f"# Log Diagnosis Report")
        sections.append("")
        sections.append(f"**Generated:** {metadata.get('generated_at', 'Unknown')}")
        sections.append(f"**Diagnosis ID:** `{metadata.get('diagnosis_id', 'Unknown')}`")
        sections.append(f"**Processing Time:** {metadata.get('processing_time_seconds', 0):.2f} seconds")
        sections.append("")
        
        # Executive Summary
        sections.append("## Executive Summary")
        sections.append("")
        sections.append(diagnosis_result.get('summary', 'No summary available'))
        sections.append("")
        
        # Confidence Score
        confidence = diagnosis_result.get('confidence_score', 0.0)
        confidence_bar = self._create_confidence_bar(confidence)
        sections.append(f"**Confidence Score:** {confidence:.1%} {confidence_bar}")
        sections.append("")
        
        # Error Details
        sections.append("## Error Details")
        sections.append("")
        sections.append("### Log Information")
        sections.append("")
        sections.append(f"- **Timestamp:** {parsed_log.get('timestamp', 'Unknown')}")
        sections.append(f"- **Log Level:** `{parsed_log.get('level', 'Unknown')}`")
        sections.append(f"- **Source:** {parsed_log.get('source') or 'Unknown'}")
        sections.append(f"- **Service:** {parsed_log.get('service_name') or 'Unknown'}")
        sections.append("")
        
        # Original Log Message
        sections.append("### Original Log Message")
        sections.append("")
        sections.append("```")
        sections.append(parsed_log.get('message', 'No message available'))
        sections.append("```")
        sections.append("")
        
        # Stack Trace (if available)
        if parsed_log.get('stack_trace'):
            sections.append("### Stack Trace")
            sections.append("")
            sections.append("```")
            sections.append(parsed_log['stack_trace'])
            sections.append("```")
            sections.append("")
        
        # Extracted Error Patterns
        if parsed_log.get('extracted_errors'):
            sections.append("### Extracted Error Patterns")
            sections.append("")
            for i, error in enumerate(parsed_log['extracted_errors'], 1):
                sections.append(f"{i}. `{error}`")
            sections.append("")
        
        # Root Cause Analysis
        if diagnosis_result.get('root_cause'):
            sections.append("## Root Cause Analysis")
            sections.append("")
            sections.append(diagnosis_result['root_cause'])
            sections.append("")
        
        # Technical Analysis
        if diagnosis_result.get('error_analysis'):
            sections.append("## Technical Analysis")
            sections.append("")
            sections.append(diagnosis_result['error_analysis'])
            sections.append("")
        
        # Repository Context
        sections.append("## Repository Context")
        sections.append("")
        sections.append(f"- **Branch:** `{git_info.get('branch', 'Unknown')}`")
        sections.append(f"- **Current Commit:** `{git_info.get('current_commit', 'Unknown')[:12]}`")
        sections.append(f"- **Last Pull:** {git_info.get('last_pull_time', 'Unknown')}")
        sections.append("")
        
        # Recent Commits
        recent_commits = git_info.get('recent_commits', [])
        if recent_commits:
            sections.append("### Recent Commits")
            sections.append("")
            for commit in recent_commits[:5]:  # Show top 5
                sections.append(f"#### {commit.get('short_hash', commit.get('hash', 'Unknown')[:12])} - {commit.get('message', 'No message')}")
                sections.append(f"**Author:** {commit.get('author', 'Unknown')} | **Date:** {commit.get('date', 'Unknown')}")
                
                if commit.get('changed_files'):
                    sections.append("**Changed Files:**")
                    for file_path in commit['changed_files'][:10]:  # Limit to 10 files
                        sections.append(f"- `{file_path}`")
                sections.append("")
        
        # Recently Changed Files
        changed_files = git_info.get('changed_files', [])
        if changed_files:
            sections.append("### Recently Changed Files")
            sections.append("")
            for file_path in changed_files[:20]:  # Show up to 20 files
                sections.append(f"- `{file_path}`")
            sections.append("")
        
        # Relevant Code Files
        relevant_files = diagnosis_result.get('relevant_code_files', [])
        if relevant_files:
            sections.append("## Relevant Code Files")
            sections.append("")
            sections.append("The following files are most likely related to this error:")
            sections.append("")
            
            for file_item in relevant_files:
                file_path = file_item.get('file_path', 'Unknown')
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
            
            sections.append("")
        
        # Recommendations
        recommendations = diagnosis_result.get('recommendations', [])
        if recommendations:
            sections.append("## Recommendations")
            sections.append("")
            
            # Format recommendations properly
            formatted_recommendations = self._format_recommendations(recommendations)
            
            for i, recommendation in enumerate(formatted_recommendations, 1):
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
        sections.append(f"- **Report ID:** `{json_report.get('report_id', 'Unknown')}`")
        sections.append(f"- **Diagnosis ID:** `{metadata.get('diagnosis_id', 'Unknown')}`")
        sections.append(f"- **Version:** {json_report.get('version', '2.0')}")
        sections.append(f"- **Generated At:** {metadata.get('generated_at', 'Unknown')}")
        
        return "\n".join(sections)
    
    def stream_markdown(self, json_report: Dict[str, Any]) -> Iterator[str]:
        """Stream markdown generation for large reports"""
        # For now, just yield the complete markdown
        # This can be optimized later for very large reports
        yield self.generate_from_json(json_report)
    
    def _create_confidence_bar(self, confidence: float) -> str:
        """Create a visual confidence bar"""
        filled_blocks = int(confidence * 10)
        empty_blocks = 10 - filled_blocks
        
        filled = "█" * filled_blocks
        empty = "░" * empty_blocks
        
        return f"[{filled}{empty}]"
    
    def _format_recommendations(self, recommendations: List[str]) -> List[Dict[str, Any]]:
        """Format and group recommendations properly"""
        if not recommendations:
            return []
        
        formatted_recommendations = []
        
        # Join all recommendations into a single text block for processing
        full_text = "\n".join(recommendations)
        
        # Split by common recommendation indicators
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
                j = 0
                while j < len(lines[1:]):  # Skip the title line
                    line = lines[j + 1]  # +1 because we're skipping the title
                    if not line:
                        j += 1
                        continue
                    
                    # Check if this line and the next should be joined (like broken printf statements)
                    if (j + 2 < len(lines) and 
                        line.endswith('"') == False and 
                        'printf(' in line and
                        lines[j + 2].startswith('", ')):
                        # Join broken printf statement
                        next_line = lines[j + 2]
                        joined_line = line + '\\n' + next_line
                        processed_lines.append(joined_line)
                        j += 2  # Skip the next line since we've joined it
                    else:
                        processed_lines.append(line)
                        j += 1
                
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
