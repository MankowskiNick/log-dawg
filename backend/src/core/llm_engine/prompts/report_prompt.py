"""
Report prompt builder for Stage 1 - Natural language analysis
"""
from pathlib import Path
from typing import List, Optional
from src.models.schemas import ParsedLogEntry, GitInfo, GitCommitInfo
from .base import BasePromptBuilder


class ReportPromptBuilder(BasePromptBuilder):
    """Builder for Stage 1 narrative analysis prompts"""
    
    def build_prompt(
        self, 
        parsed_log: ParsedLogEntry, 
        git_info: GitInfo, 
        recent_commits: Optional[List[GitCommitInfo]] = None,
        discovered_files: Optional[List] = None
    ) -> str:
        """Build comprehensive analysis prompt for natural language report"""
        
        prompt_parts = [
            "# Log Analysis Request",
            "",
            "You are an expert software engineer and debugging specialist. Please analyze the following error log and provide a comprehensive diagnostic report in natural language.",
            "",
            "Focus on providing detailed analysis, clear explanations, and actionable insights. Write as if you're explaining the issue to a fellow developer who needs to understand and fix the problem.",
            "",
            "## Error Log Details",
            f"**Timestamp:** {parsed_log.timestamp or 'Unknown'}",
            f"**Log Level:** {parsed_log.level}",
            f"**Source:** {parsed_log.source or 'Unknown'}",
            f"**Service:** {parsed_log.service_name or 'Unknown'}",
            "",
            "### Log Message",
            "```",
            parsed_log.message,
            "```",
            ""
        ]
        
        # Add stack trace if available
        if parsed_log.stack_trace:
            prompt_parts.extend([
                "### Stack Trace",
                "```",
                parsed_log.stack_trace,
                "```",
                ""
            ])
        
        # Add extracted errors
        if parsed_log.extracted_errors:
            prompt_parts.extend([
                "### Extracted Error Patterns",
                ""
            ])
            for i, error in enumerate(parsed_log.extracted_errors, 1):
                prompt_parts.append(f"{i}. {error}")
            prompt_parts.append("")
        
        # Add git context
        prompt_parts.extend([
            "## Repository Context",
            f"**Current Branch:** {git_info.branch}",
            f"**Latest Commit:** {git_info.current_commit[:8]}",
            f"**Last Pull:** {git_info.last_pull_time}",
            ""
        ])
        
        # Add recent commits
        if git_info.recent_commits:
            prompt_parts.extend([
                "### Recent Commits",
                ""
            ])
            for commit in git_info.recent_commits[:3]:  # Limit to 3 most recent
                prompt_parts.extend([
                    f"**{commit['short_hash']}** by {commit['author']}",
                    f"Date: {commit['date']}",
                    f"Message: {commit['message']}",
                    f"Changed files: {', '.join(commit['changed_files'][:5])}{'...' if len(commit['changed_files']) > 5 else ''}",
                    ""
                ])
        
        # Add changed files context
        if git_info.changed_files:
            prompt_parts.extend([
                "### Recently Changed Files",
                ""
            ])
            for file_path in git_info.changed_files[:10]:  # Limit to 10 files
                prompt_parts.append(f"- {file_path}")
            prompt_parts.append("")
        
        # Add detailed commit analysis if available
        if recent_commits:
            prompt_parts.extend([
                "### Detailed Recent Changes",
                ""
            ])
            for commit in recent_commits[:2]:  # Limit to 2 most recent
                prompt_parts.extend([
                    f"#### Commit {commit.hash[:8]} - {commit.message}",
                    f"**Author:** {commit.author}",
                    f"**Date:** {commit.date}",
                    f"**Changes:** +{commit.additions} -{commit.deletions}",
                    "**Modified Files:**"
                ])
                for file_path in commit.changed_files[:5]:
                    prompt_parts.append(f"- {file_path}")
                prompt_parts.append("")
        
        # Add discovered file contents if available
        if discovered_files:
            prompt_parts.extend([
                "## Relevant Code Files",
                "",
                f"The following {len(discovered_files)} files were identified as relevant to this error through context discovery:",
                ""
            ])
            
            for file_info in discovered_files:
                prompt_parts.extend([
                    f"### {file_info.file_path} ({file_info.size_kb:.1f}KB)",
                    ""
                ])
                
                if file_info.selection_reason:
                    prompt_parts.extend([
                        f"**Relevance:** {file_info.selection_reason}",
                        ""
                    ])
                
                if file_info.snippets:
                    for snippet in file_info.snippets:
                        prompt_parts.extend([
                            f"**Snippet (lines {snippet.start_line}-{snippet.end_line}):**",
                            "```",
                            snippet.content,
                            "```",
                            ""
                        ])
                elif file_info.content:
                    prompt_parts.extend([
                        "```",
                        file_info.content,
                        "```",
                        ""
                    ])
        
        # Add analysis instructions
        prompt_parts.extend(self._get_analysis_instructions())
        
        return "\n".join(prompt_parts)
    
    def _get_analysis_instructions(self) -> List[str]:
        """Get the analysis instructions for natural language report"""
        return [
            "## Analysis Instructions",
            "",
            "Please provide a comprehensive diagnostic report that includes:",
            "",
            "### 1. Executive Summary",
            "- Brief overview of the error and its impact",
            "- Severity assessment",
            "- Immediate concerns or risks",
            "",
            "### 2. Root Cause Analysis",
            "- Detailed investigation of what caused this error",
            "- Reference specific code snippets with file names and line numbers",
            "- Explain the sequence of events that led to the failure",
            "- Identify any contributing factors or conditions",
            "",
            "### 3. Technical Analysis",
            "- Deep dive into the technical aspects of the error",
            "- Explain error patterns and their significance",
            "- Analyze stack traces and error messages",
            "- Discuss any relevant code patterns or architectural issues",
            "",
            "### 4. Impact Assessment",
            "- What functionality is affected",
            "- Potential user impact",
            "- System stability concerns",
            "- Performance implications",
            "",
            "### 5. Recommendations",
            "- Specific steps to fix the immediate issue",
            "- Code changes needed (with examples where possible)",
            "- Configuration adjustments",
            "- Testing strategies to verify the fix",
            "- Preventive measures to avoid similar issues",
            "",
            "### 6. Related Files and Components",
            "- List files that are directly related to this error",
            "- Identify components or modules that may need attention",
            "- Suggest areas for additional investigation",
            "",
            "### 7. Confidence Assessment",
            "- How confident are you in this analysis?",
            "- What additional information would improve the diagnosis?",
            "- Any assumptions made during the analysis",
            "",
            "## Writing Guidelines",
            "",
            "- Write in clear, professional language with rich technical detail",
            "- Use specific code references with exact file names and line numbers",
            "- Include actual code snippets when relevant to the analysis",
            "- Provide actionable recommendations with concrete implementation steps",
            "- Explain complex concepts clearly with technical precision",
            "- Use bullet points and structured formatting for readability",
            "- Reference specific functions, variables, and code patterns by name",
            "- Include exact error messages and stack trace analysis",
            "- Provide code examples for recommended fixes when possible",
            "",
            "## Technical Detail Requirements",
            "",
            "- Quote exact error messages and stack traces",
            "- Reference specific code lines and functions",
            "- Include variable names, method calls, and class references",
            "- Provide concrete code examples for fixes and improvements",
            "- Explain technical concepts with implementation details",
            "- Reference configuration files, settings, and environment details",
            "",
            "Focus on being thorough, accurate, and technically detailed. This report will be converted to structured JSON format, so include all relevant code references, technical terms, and implementation details that will benefit from rich markdown formatting."
        ]
