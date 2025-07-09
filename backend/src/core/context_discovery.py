"""
Context Discovery Engine for intelligent file selection
"""
import os
import json
import asyncio
import fnmatch
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from src.models.schemas import (
    ParsedLogEntry, GitInfo, ContextDiscoveryRequest, ContextDiscoveryResponse,
    FileContentInfo, ContextDiscoveryResult, CodeSnippet
)
from src.core.config import config_manager
from src.core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class FileRelevanceScore:
    """Scoring for file relevance"""
    file_path: str
    base_score: float
    stack_trace_mention: float
    recent_changes: float
    error_pattern_match: float
    file_type_priority: float
    total_score: float
    reasoning: str

class FileStructureAnalyzer:
    """Analyzes repository structure and generates summaries"""
    
    def __init__(self, repo_path: str, config: Any):
        self.repo_path = Path(repo_path)
        self.config = config
        self.exclude_patterns = config.context_discovery.exclude_patterns
        self.priority_extensions = config.context_discovery.file_extensions_priority
        
        logger.info(
            f"Initialized FileStructureAnalyzer for repository",
            extra={
                'repo_path': str(repo_path),
                'repo_exists': self.repo_path.exists(),
                'exclude_patterns': self.exclude_patterns,
                'priority_extensions': self.priority_extensions,
                'exclude_pattern_count': len(self.exclude_patterns),
                'priority_extension_count': len(self.priority_extensions)
            }
        )
        
    def generate_structure_summary(self, max_depth: int = 3) -> str:
        """Generate a structured summary of the repository"""
        logger.debug(f"Generating repository structure summary with max_depth={max_depth}")
        
        if not self.repo_path.exists():
            logger.warning(f"Repository path does not exist: {self.repo_path}")
            return "Repository path does not exist"
        
        structure_lines = []
        structure_lines.append(f"Repository Structure: {self.repo_path.name}")
        structure_lines.append("=" * 50)
        
        # Generate tree structure
        logger.debug("Generating directory tree structure")
        tree_lines = self._generate_tree(self.repo_path, max_depth=max_depth)
        structure_lines.extend(tree_lines)
        
        # Add file type summary
        logger.debug("Analyzing file types for summary")
        file_stats = self._analyze_file_types()
        structure_lines.append("\nFile Type Summary:")
        structure_lines.append("-" * 20)
        for ext, count in sorted(file_stats.items()):
            structure_lines.append(f"{ext}: {count} files")
        
        logger.info(
            f"Generated repository structure summary",
            extra={
                'max_depth': max_depth,
                'total_file_types': len(file_stats),
                'total_files': sum(file_stats.values()),
                'structure_length': len("\n".join(structure_lines))
            }
        )
        
        return "\n".join(structure_lines)
    
    def _generate_tree(self, path: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0) -> List[str]:
        """Generate tree structure recursively"""
        if current_depth >= max_depth:
            logger.debug(f"Reached max depth {max_depth} at path: {path}")
            return []

        lines = []
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
            original_count = len(entries)
            entries = [e for e in entries if not self._should_exclude(e)]
            excluded_count = original_count - len(entries)

            if excluded_count > 0:
                logger.debug(
                    f"Excluded {excluded_count} entries from {path}",
                    extra={
                        'path': str(path),
                        'original_count': original_count,
                        'filtered_count': len(entries),
                        'excluded_count': excluded_count
                    }
                )

            for i, entry in enumerate(entries):
                is_last = i == len(entries) - 1
                current_prefix = "└── " if is_last else "├── "
                next_prefix = "    " if is_last else "│   "

                display_name = entry.name
                if entry.is_file():
                    try:
                        size_kb = entry.stat().st_size / 1024
                        if size_kb > 1024:
                            size_str = f"({size_kb/1024:.1f}MB)"
                        else:
                            size_str = f"({size_kb:.1f}KB)"
                        display_name += f" {size_str}"
                    except OSError as e:
                        logger.debug(f"Could not get size for {entry}: {e}")
                        display_name += " (size unknown)"

                lines.append(f"{prefix}{current_prefix}{display_name}")

                if entry.is_dir() and current_depth < max_depth - 1:
                    subtree = self._generate_tree(
                        entry,
                        prefix + next_prefix,
                        max_depth,
                        current_depth + 1
                    )
                    lines.extend(subtree)

        except PermissionError as e:
            logger.warning(f"Permission denied accessing {path}: {e}")
            lines.append(f"{prefix}[Permission Denied]")
        except Exception as e:
            logger.error(f"Error generating tree for {path}: {e}")
            lines.append(f"{prefix}[Error: {e}]")

        # Add line numbers
        numbered_lines = [f"{i+1:4d} | {line}" for i, line in enumerate(lines)]

        return numbered_lines
    
    def _should_exclude(self, path: Path) -> bool:
        """Check if path should be excluded based on patterns"""
        relative_path = str(path.relative_to(self.repo_path))
        
        # Always exclude common binary/non-code file extensions
        binary_extensions = {
            '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg',
            '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',
            '.mp3', '.wav', '.ogg', '.flac', '.aac',
            '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar',
            '.exe', '.dll', '.so', '.dylib', '.bin',
            '.docx', '.xlsx', '.pptx', '.doc', '.xls', '.ppt',
            '.ico', '.cur', '.ttf', '.otf', '.woff', '.woff2',
            '.db', '.sqlite', '.sqlite3'
        }
        
        if path.suffix.lower() in binary_extensions:
            return True
        
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(relative_path, pattern) or fnmatch.fnmatch(path.name, pattern):
                return True
        
        return False
    
    def _analyze_file_types(self) -> Dict[str, int]:
        """Analyze file types in the repository"""
        file_stats = {}
        total_files_scanned = 0
        excluded_files = 0
        
        logger.debug("Starting file type analysis")
        
        try:
            for file_path in self.repo_path.rglob("*"):
                if file_path.is_file():
                    total_files_scanned += 1
                    if not self._should_exclude(file_path):
                        ext = file_path.suffix or "[no extension]"
                        file_stats[ext] = file_stats.get(ext, 0) + 1
                    else:
                        excluded_files += 1
        except Exception as e:
            logger.error(f"Error during file type analysis: {e}")
        
        logger.info(
            f"File type analysis completed",
            extra={
                'total_files_scanned': total_files_scanned,
                'included_files': sum(file_stats.values()),
                'excluded_files': excluded_files,
                'unique_extensions': len(file_stats),
                'file_type_breakdown': dict(sorted(file_stats.items(), key=lambda x: x[1], reverse=True)[:10])  # Top 10
            }
        )
        
        return file_stats
    
    def score_file_relevance(
        self, 
        file_path: str, 
        parsed_log: ParsedLogEntry, 
        git_info: GitInfo
    ) -> FileRelevanceScore:
        """Score file relevance based on multiple factors"""
        path = Path(file_path)
        
        logger.debug(f"Scoring file relevance for: {file_path}")
        
        # Base score
        base_score = 0.1
        
        # Stack trace mentions
        stack_trace_score = 0.0
        stack_trace_reasoning = ""
        if parsed_log.stack_trace:
            # Check for exact path match
            if file_path in parsed_log.stack_trace:
                stack_trace_score = 0.8
                stack_trace_reasoning = "mentioned in stack trace"
                logger.debug(f"File {file_path} found in stack trace (exact match)")
            else:
                # Check for filename match (without path)
                filename = path.name
                if filename in parsed_log.stack_trace:
                    stack_trace_score = 0.7
                    stack_trace_reasoning = f"filename '{filename}' mentioned in stack trace"
                    logger.debug(f"Filename {filename} found in stack trace")
                # Check for filename without extension
                elif path.stem in parsed_log.stack_trace:
                    stack_trace_score = 0.6
                    stack_trace_reasoning = f"filename stem '{path.stem}' mentioned in stack trace"
                    logger.debug(f"Filename stem {path.stem} found in stack trace")
        
        # Recent changes
        recent_changes_score = 0.0
        recent_changes_reasoning = ""
        if file_path in git_info.changed_files:
            recent_changes_score = 0.6
            recent_changes_reasoning = "recently changed in git"
            logger.debug(f"File {file_path} was recently changed in git")
        
        # Error pattern matching
        error_pattern_score = 0.0
        error_pattern_reasoning = ""
        for error in parsed_log.extracted_errors:
            if any(keyword in path.name.lower() for keyword in error.lower().split()):
                error_pattern_score = 0.4
                error_pattern_reasoning = f"filename matches error pattern: {error}"
                logger.debug(f"File {file_path} matches error pattern: {error}")
                break
        
        # File type priority
        file_type_score = 0.0
        file_type_reasoning = ""
        if path.suffix in self.priority_extensions:
            priority_index = self.priority_extensions.index(path.suffix)
            file_type_score = 0.3 * (1 - priority_index / len(self.priority_extensions))
            file_type_reasoning = f"priority file type: {path.suffix}"
            logger.debug(f"File {file_path} has priority extension {path.suffix} (index {priority_index})")
        
        total_score = (
            base_score + 
            stack_trace_score + 
            recent_changes_score + 
            error_pattern_score + 
            file_type_score
        )
        
        reasoning_parts = [r for r in [
            stack_trace_reasoning, recent_changes_reasoning, 
            error_pattern_reasoning, file_type_reasoning
        ] if r]
        
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "low base relevance"
        
        score_result = FileRelevanceScore(
            file_path=file_path,
            base_score=base_score,
            stack_trace_mention=stack_trace_score,
            recent_changes=recent_changes_score,
            error_pattern_match=error_pattern_score,
            file_type_priority=file_type_score,
            total_score=total_score,
            reasoning=reasoning
        )
        
        if total_score > 0.5:  # Log high-scoring files
            logger.info(
                f"High relevance score for file: {file_path}",
                extra={
                    'file_path': file_path,
                    'total_score': round(total_score, 3),
                    'score_breakdown': {
                        'base': base_score,
                        'stack_trace': stack_trace_score,
                        'recent_changes': recent_changes_score,
                        'error_pattern': error_pattern_score,
                        'file_type': file_type_score
                    },
                    'reasoning': reasoning
                }
            )
        
        return score_result
    
    def get_candidate_files(self, parsed_log: ParsedLogEntry, git_info: GitInfo) -> List[FileRelevanceScore]:
        """Get and rank candidate files for context discovery"""
        logger.info("Starting candidate file discovery and ranking")
        
        candidates = []
        total_files_scanned = 0
        excluded_files = 0
        
        try:
            for file_path in self.repo_path.rglob("*"):
                if file_path.is_file():
                    total_files_scanned += 1
                    if not self._should_exclude(file_path):
                        relative_path = str(file_path.relative_to(self.repo_path))
                        score = self.score_file_relevance(relative_path, parsed_log, git_info)
                        candidates.append(score)
                    else:
                        excluded_files += 1
        except Exception as e:
            logger.error(f"Error during candidate file discovery: {e}")
            raise
        
        # Sort by total score descending
        candidates.sort(key=lambda x: x.total_score, reverse=True)
        
        # Log top candidates
        top_candidates = candidates[:10]  # Top 10
        logger.info(
            f"Candidate file ranking completed",
            extra={
                'total_files_scanned': total_files_scanned,
                'excluded_files': excluded_files,
                'candidate_files': len(candidates),
                'top_candidates': [
                    {
                        'file_path': c.file_path,
                        'score': round(c.total_score, 3),
                        'reasoning': c.reasoning
                    }
                    for c in top_candidates
                ]
            }
        )
        
        return candidates

class ContextValidator:
    """Validates context completeness and quality"""
    
    def __init__(self, config: Any):
        self.config = config
        self.confidence_threshold = config.context_discovery.confidence_threshold
        self.min_improvement = config.context_discovery.min_confidence_improvement
        
        logger.info(
            "Initialized ContextValidator",
            extra={
                'confidence_threshold': self.confidence_threshold,
                'min_improvement': self.min_improvement,
                'max_iterations': config.context_discovery.max_iterations,
                'max_context_size_kb': config.context_discovery.max_total_context_size_kb
            }
        )
    
    def should_continue_discovery(
        self,
        iteration: int,
        confidence_history: List[float],
        current_context_size_kb: float
    ) -> Tuple[bool, str]:
        """Determine if context discovery should continue"""

        logger.debug(
            f"Evaluating whether to continue discovery (iteration {iteration})",
            extra={
                'iteration': iteration,
                'current_context_size_kb': current_context_size_kb,
                'confidence_history': confidence_history,
                'max_iterations': self.config.context_discovery.max_iterations,
                'max_context_size_kb': self.config.context_discovery.max_total_context_size_kb,
                'confidence_threshold': self.confidence_threshold,
                'min_improvement': self.min_improvement
            }
        )

        # Check max iterations
        if iteration > self.config.context_discovery.max_iterations:
            reason = f"Maximum iterations reached ({iteration})"
            logger.info(f"Stopping discovery: {reason}")
            return False, reason

        # Check context size limit
        if current_context_size_kb >= self.config.context_discovery.max_total_context_size_kb:
            reason = f"Context size limit reached ({current_context_size_kb:.1f}KB)"
            logger.info(f"Stopping discovery: {reason}")
            return False, reason

        # Check confidence threshold
        if confidence_history and confidence_history[-1] >= self.confidence_threshold:
            reason = f"Confidence threshold reached ({confidence_history[-1]:.2f})"
            logger.info(f"Stopping discovery: {reason}")
            return False, reason
        
        # Check confidence improvement
        if len(confidence_history) >= 2:
            improvement = confidence_history[-1] - confidence_history[-2]
            if improvement < self.min_improvement:
                reason = f"Insufficient confidence improvement ({improvement:.2f})"
                logger.info(f"Stopping discovery: {reason}")
                return False, reason
        
        logger.debug("Discovery should continue")
        return True, "Continue discovery"
    
    def calculate_context_quality_score(
        self, 
        files_analyzed: List[str],
        total_size_kb: float,
        confidence_progression: List[float]
    ) -> float:
        """Calculate overall context quality score"""
        logger.debug("Calculating context quality score")
        
        if not confidence_progression:
            logger.warning("No confidence progression data available for quality score")
            return 0.0
        
        # Base score from final confidence
        base_score = confidence_progression[-1]
        
        # Bonus for file diversity
        file_extensions = set(Path(f).suffix for f in files_analyzed)
        diversity_bonus = min(0.1, len(file_extensions) * 0.02)
        
        # Penalty for excessive size
        size_penalty = 0.0
        size_threshold = self.config.context_discovery.max_total_context_size_kb * 0.8
        if total_size_kb > size_threshold:
            size_penalty = 0.1
        
        # Bonus for confidence improvement
        improvement_bonus = 0.0
        if len(confidence_progression) > 1:
            total_improvement = confidence_progression[-1] - confidence_progression[0]
            improvement_bonus = min(0.1, total_improvement * 0.1)
        
        final_score = base_score + diversity_bonus + improvement_bonus - size_penalty
        final_score = max(0.0, min(1.0, final_score))
        
        logger.info(
            f"Context quality score calculated: {final_score:.3f}",
            extra={
                'final_score': final_score,
                'base_score': base_score,
                'diversity_bonus': diversity_bonus,
                'improvement_bonus': improvement_bonus,
                'size_penalty': size_penalty,
                'files_analyzed_count': len(files_analyzed),
                'unique_extensions': len(file_extensions),
                'total_size_kb': total_size_kb,
                'confidence_progression': confidence_progression
            }
        )
        
        return final_score

class ContextDiscoveryEngine:
    """Main engine for context discovery"""
    
    def __init__(self, llm_provider):
        self.config = config_manager.config
        self.llm_provider = llm_provider
        self.file_analyzer = FileStructureAnalyzer(
            self.config.repository.local_path, 
            self.config
        )
        self.validator = ContextValidator(self.config)
        
        logger.info(
            "Initialized ContextDiscoveryEngine",
            extra={
                'repository_path': self.config.repository.local_path,
                'discovery_enabled': self.config.context_discovery.enabled,
                'max_iterations': self.config.context_discovery.max_iterations,
                'confidence_threshold': self.config.context_discovery.confidence_threshold,
                'max_context_size_kb': self.config.context_discovery.max_total_context_size_kb,
                'file_size_limit_kb': self.config.context_discovery.file_size_limit_kb,
                'llm_provider': self.config.llm.provider,
                'llm_model': self.config.llm.model
            }
        )
    
    async def discover_context(
        self, 
        parsed_log: ParsedLogEntry, 
        git_info: GitInfo,
        diagnosis_logger = None
    ) -> ContextDiscoveryResult:
        """Main context discovery process"""
        
        if not self.config.context_discovery.enabled:
            logger.info("Context discovery disabled, skipping")
            return self._create_empty_result()
        
        if diagnosis_logger:
            diagnosis_logger.log_info("Starting context discovery")
        
        logger.info("Starting context discovery process")
        
        # Initialize discovery state
        discovered_files = []
        confidence_history = []
        discovery_reasoning = []
        total_context_size = 0.0
        iteration = 0
        
        # Generate initial file structure
        if diagnosis_logger:
            diagnosis_logger.log_repository_scan_start(
                scan_type="structure_summary",
                parameters={'max_depth': 3}
            )
        
        file_structure = self.file_analyzer.generate_structure_summary()
        
        if diagnosis_logger:
            diagnosis_logger.log_repository_scan_result(
                scan_type="structure_summary",
                result={
                    'structure_length': len(file_structure),
                    'lines_count': len(file_structure.split('\n'))
                }
            )
        
        # Get initial candidate files based on relevance scoring
        if diagnosis_logger:
            diagnosis_logger.log_repository_scan_start(
                scan_type="candidate_file_ranking",
                parameters={
                    'error_message': parsed_log.message[:100] + "..." if len(parsed_log.message) > 100 else parsed_log.message,
                    'has_stack_trace': bool(parsed_log.stack_trace),
                    'changed_files_count': len(git_info.changed_files) if git_info.changed_files else 0
                }
            )
        
        candidates = self.file_analyzer.get_candidate_files(parsed_log, git_info)
        
        if diagnosis_logger:
            diagnosis_logger.log_repository_scan_result(
                scan_type="candidate_file_ranking",
                result={
                    'total_candidates': len(candidates),
                    'high_score_candidates': len([c for c in candidates if c.total_score > 0.5]),
                    'top_10_scores': [round(c.total_score, 3) for c in candidates[:10]]
                }
            )
        
        # Include top candidates initially
        initial_files = [c.file_path for c in candidates[:3]]
        
        # Add initial files to discovered_files and calculate sizes
        for file_path in initial_files:
            if diagnosis_logger:
                diagnosis_logger.log_file_analysis_start(
                    file_path=file_path,
                    analysis_type="initial_content_load"
                )
            
            file_info = self._load_file_content(file_path)
            if file_info and file_info.size_kb is not None:
                discovered_files.append(file_path)
                total_context_size += file_info.size_kb
                
                if diagnosis_logger:
                    diagnosis_logger.log_file_selection_decision(
                        file_path=file_path,
                        decision="SELECTED_INITIAL",
                        reasoning=f"Top candidate file (score: {next((c.total_score for c in candidates if c.file_path == file_path), 'unknown')})",
                        metadata={
                            'file_size_kb': file_info.size_kb,
                            'selection_phase': 'initial'
                        }
                    )
                    
                    diagnosis_logger.log_file_analysis_result(
                        file_path=file_path,
                        analysis_type="initial_content_load",
                        result={
                            'loaded_successfully': True,
                            'size_kb': file_info.size_kb,
                            'line_count': len(file_info.content.split('\n')) if file_info.content else 0
                        }
                    )
            elif diagnosis_logger:
                diagnosis_logger.log_file_analysis_result(
                    file_path=file_path,
                    analysis_type="initial_content_load",
                    result={
                        'loaded_successfully': False,
                        'reason': 'File not found or too large'
                    }
                )
        
        if diagnosis_logger:
            diagnosis_logger.log_debug(
                f"Initial candidate files: {initial_files}",
                metadata={
                    'candidate_count': len(candidates),
                    'initial_files_loaded': len(discovered_files),
                    'initial_size_kb': total_context_size
                }
            )
        
        while True:
            iteration += 1
            
            if diagnosis_logger:
                # Log iteration start
                diagnosis_logger.log_context_discovery_iteration_start(
                    iteration=iteration,
                    metadata={
                        'current_files_count': len(discovered_files),
                        'current_context_size_kb': round(total_context_size, 2),
                        'confidence_history': confidence_history
                    }
                )
                
                with diagnosis_logger.log_step(f"context_discovery_iteration_{iteration}"):
                    # Check if we should continue
                    should_continue, reason = self.validator.should_continue_discovery(
                        iteration, confidence_history, total_context_size
                    )
                    
                    # Log the sufficiency check decision
                    diagnosis_logger.log_context_sufficiency_check(
                        iteration=iteration,
                        should_continue=should_continue,
                        reason=reason,
                        context_metrics={
                            'current_files_count': len(discovered_files),
                            'current_context_size_kb': round(total_context_size, 2),
                            'confidence_history': confidence_history,
                            'max_iterations': self.config.context_discovery.max_iterations,
                            'confidence_threshold': self.config.context_discovery.confidence_threshold,
                            'max_context_size_kb': self.config.context_discovery.max_total_context_size_kb
                        }
                    )
                    
                    if not should_continue:
                        diagnosis_logger.log_info(f"Stopping discovery: {reason}")
                        break
                    
                    # Perform discovery iteration
                    iteration_result = await self._perform_discovery_iteration(
                        parsed_log, file_structure, discovered_files, 
                        confidence_history, iteration, diagnosis_logger
                    )
                    
                    if iteration_result is None:
                        diagnosis_logger.log_info("Discovery iteration failed, stopping")
                        break
                    
                    new_files, confidence, reasoning = iteration_result
                    
                    # Log confidence progression
                    previous_confidence = confidence_history[-1] if confidence_history else None
                    diagnosis_logger.log_confidence_progression(
                        iteration=iteration,
                        confidence_score=confidence,
                        previous_score=previous_confidence,
                        reasoning=reasoning
                    )
                    
                    # Update state
                    confidence_history.append(confidence)
                    discovery_reasoning.append(reasoning)
                    
                    # Add new files and calculate sizes
                    files_added_this_iteration = []
                    for file_path in new_files:
                        if file_path not in discovered_files:
                            file_info = self._load_file_content(file_path)
                            if file_info and file_info.size_kb is not None:
                                discovered_files.append(file_path)
                                total_context_size += file_info.size_kb
                                files_added_this_iteration.append(file_path)
                                
                                # Log individual file selection decision
                                diagnosis_logger.log_file_selection_decision(
                                    file_path=file_path,
                                    decision="SELECTED_BY_LLM",
                                    reasoning=f"LLM iteration {iteration}: {reasoning}",
                                    metadata={
                                        'file_size_kb': file_info.size_kb,
                                        'iteration': iteration,
                                        'confidence_score': confidence
                                    }
                                )
                    
                    # Log iteration completion
                    diagnosis_logger.log_context_discovery_iteration_end(
                        iteration=iteration,
                        result={
                            'files_requested': new_files,
                            'files_added': files_added_this_iteration,
                            'confidence_score': confidence,
                            'reasoning': reasoning,
                            'total_files_now': len(discovered_files),
                            'total_size_kb_now': round(total_context_size, 2)
                        }
                    )
            else:
                # No diagnosis logger, run simplified version
                should_continue, reason = self.validator.should_continue_discovery(
                    iteration, confidence_history, total_context_size
                )
                
                if not should_continue:
                    logger.info(f"Stopping discovery: {reason}")
                    break
                
                iteration_result = await self._perform_discovery_iteration(
                    parsed_log, file_structure, discovered_files, 
                    confidence_history, iteration
                )
                
                if iteration_result is None:
                    logger.info("Discovery iteration failed, stopping")
                    break
                
                new_files, confidence, reasoning = iteration_result
                
                confidence_history.append(confidence)
                discovery_reasoning.append(reasoning)
                
                for file_path in new_files:
                    if file_path not in discovered_files:
                        file_info = self._load_file_content(file_path)
                        if file_info and file_info.size_kb is not None:
                            discovered_files.append(file_path)
                            total_context_size += file_info.size_kb
        
        final_confidence = confidence_history[-1] if confidence_history else 0.0

        # New step: Extract snippets from discovered files
        files_with_snippets = await self._extract_snippets_from_files(
            discovered_files, parsed_log, diagnosis_logger
        )
        
        # Clear content from FileContentInfo objects to avoid large response bodies
        processed_files = []
        for file_info in files_with_snippets:
            # Clear content but keep as proper FileContentInfo object
            if hasattr(file_info, 'content'):
                file_info.content = None
            processed_files.append(file_info)
            
        result = ContextDiscoveryResult(
            iterations_performed=iteration,
            files_analyzed=processed_files,
            confidence_progression=confidence_history,
            total_context_size_kb=total_context_size,
            discovery_reasoning=discovery_reasoning,
            final_confidence=final_confidence
        )
        
        if diagnosis_logger:
            diagnosis_logger.log_info(
                f"Context discovery completed: {len(discovered_files)} files, "
                f"{total_context_size:.1f}KB, confidence: {final_confidence:.2f}"
            )
        
        logger.info(
            f"Context discovery completed: {len(discovered_files)} files, "
            f"{total_context_size:.1f}KB, confidence: {final_confidence:.2f}"
        )
        
        return result
    
    async def _perform_discovery_iteration(
        self, 
        parsed_log: ParsedLogEntry,
        file_structure: str,
        current_files: List[str],
        confidence_history: List[float],
        iteration: int,
        diagnosis_logger = None
    ) -> Optional[Tuple[List[str], float, str]]:
        """Perform a single discovery iteration"""
        
        try:
            # Build discovery request
            discovery_request = ContextDiscoveryRequest(
                error_message=parsed_log.message,
                stack_trace=parsed_log.stack_trace,
                file_structure=file_structure,
                current_files=current_files,
                iteration=iteration,
                confidence_history=confidence_history
            )
            
            # Generate discovery prompt
            prompt = self._build_discovery_prompt(discovery_request, parsed_log)
            
            if diagnosis_logger:
                diagnosis_logger.log_discovery_prompt_generation(
                    iteration=iteration,
                    prompt_length=len(prompt),
                    context_info={
                        'current_files_count': len(current_files),
                        'confidence_history_length': len(confidence_history),
                        'has_stack_trace': bool(parsed_log.stack_trace),
                        'error_patterns_count': len(parsed_log.extracted_errors) if parsed_log.extracted_errors else 0
                    }
                )
                
                request_id = diagnosis_logger.log_llm_request(
                    provider=self.config.llm.provider,
                    model=self.config.llm.model,
                    prompt=prompt,
                    metadata={'discovery_iteration': iteration}
                )
            
            # Call LLM for file discovery
            response_text = await self.llm_provider.generate_diagnosis(prompt)
            
            if diagnosis_logger:
                diagnosis_logger.log_llm_response(
                    request_id=request_id,
                    response=response_text
                )
            
            # Parse discovery response
            discovery_response = self._parse_discovery_response(response_text)
            
            if diagnosis_logger:
                diagnosis_logger.log_discovery_response_parsing(
                    iteration=iteration,
                    response_length=len(response_text) if response_text else 0,
                    parsed_result={
                        'requested_files': discovery_response.requested_files,
                        'confidence_score': discovery_response.confidence_score,
                        'reasoning_length': len(discovery_response.reasoning)
                    }
                )
            
            return (
                discovery_response.requested_files,
                discovery_response.confidence_score,
                discovery_response.reasoning,
            )
            
        except Exception as e:
            if diagnosis_logger:
                diagnosis_logger.log_error(
                    f"Discovery iteration {iteration} failed: {e}",
                    error_type=type(e).__name__
                )
            
            logger.error(f"Discovery iteration {iteration} failed: {e}")
            return None

    async def _extract_snippets_from_files(
        self, 
        file_paths: List[str], 
        parsed_log: ParsedLogEntry, 
        diagnosis_logger=None
    ) -> List[FileContentInfo]:
        """Extract relevant snippets from a list of files."""
        logger.info(f"Extracting snippets from {len(file_paths)} files.")
        if diagnosis_logger:
            diagnosis_logger.log_info(f"Starting snippet extraction from {len(file_paths)} files.")

        tasks = [self._extract_snippet_for_file(file_path, parsed_log, diagnosis_logger) for file_path in file_paths]
        results = await asyncio.gather(*tasks)
        
        # Filter out None results from failed extractions
        successful_results = [res for res in results if res]
        
        logger.info(f"Successfully extracted snippets for {len(successful_results)} files.")
        if diagnosis_logger:
            diagnosis_logger.log_info(f"Snippet extraction completed for {len(successful_results)} files.")
            
        return successful_results

    async def _extract_snippet_for_file(
        self, 
        file_path: str, 
        parsed_log: ParsedLogEntry, 
        diagnosis_logger=None
    ) -> Optional[FileContentInfo]:
        """Extracts relevant snippets from a single file."""
        file_info = self._load_file_content(file_path, with_line_numbers=True)
        if not file_info or not file_info.content:
            return None

        prompt = self._build_snippet_extraction_prompt(file_info.content, parsed_log)
        
        if diagnosis_logger:
            request_id = diagnosis_logger.log_llm_request(
                provider=self.config.llm.provider,
                model=self.config.llm.model,
                prompt=prompt,
                metadata={'snippet_extraction_file': file_path}
            )

        response_text = await self.llm_provider.generate_diagnosis(prompt)
        
        if diagnosis_logger:
            diagnosis_logger.log_llm_response(request_id, response_text)

        snippets = self._parse_snippet_response(response_text, file_info.content)
        
        # Return the full FileContentInfo, content will be cleared later
        file_info.snippets = snippets
        return file_info

    def _build_snippet_extraction_prompt(self, file_content: str, parsed_log: ParsedLogEntry) -> str:
        """Builds a prompt to ask the LLM to extract snippets."""
        return f"""
# Task: Extract Relevant Code Snippets

You are an expert software engineer analyzing a file to find code snippets relevant to a specific error.

## Error Information
- **Error Message:** {parsed_log.message}
- **Stack Trace:**
```
{parsed_log.stack_trace or "Not available"}
```

## File Content
```
{file_content}
```

## Instructions
1.  Carefully review the file content and the error information.
2.  Identify the most relevant lines of code that are likely related to the error. This could be the function that threw the error, a configuration block, or a specific logic path.
3.  Extract these lines as one or more snippets.
4.  For each snippet, provide the starting and ending line number.
6.  Only include snippets that have demonstrable relevance to the error, do NOT include snippets that are not related or are very tangentially related.  For example, don't include JavaScript frontend configuration files if the error is related to a .NET runtime error in the backend.
5.  Keep snippets relatively short(10-20 linees) to maintain focus on the relevant code.  Reports should NEVER contain snippets more than 50 lines.

## Response Format
Provide your response in the following format. Do not include any other text or explanations.

**SNIPPETS:**
- START_LINE: 42
- END_LINE: 55

- START_LINE: 101
- END_LINE: 105
"""

    def _parse_snippet_response(self, response_text: str, file_content: str) -> List[CodeSnippet]:
        """Parses the LLM response to extract code snippets."""
        snippets = []
        lines = file_content.splitlines()
        fallback_used = False

        try:
            current_start = None
            for line in response_text.splitlines():
                if line.startswith("- START_LINE:"):
                    start_val = line.split(":")[1].strip()
                    if start_val.isdigit():
                        current_start = int(start_val)
                    else:
                        if not fallback_used:
                            logger.warning(f"Invalid START_LINE '{start_val}' in snippet response, including full file as snippet.")
                            snippets.append(CodeSnippet(
                                start_line=1,
                                end_line=len(lines),
                                content="\n".join(lines)
                            ))
                            fallback_used = True
                        current_start = None
                elif line.startswith("- END_LINE:") and current_start is not None:
                    end_val = line.split(":")[1].strip()
                    if end_val.isdigit():
                        current_end = int(end_val)
                        # Ensure line numbers are valid
                        start_idx = max(0, current_start - 1)
                        end_idx = min(len(lines), current_end)
                        if start_idx < end_idx:
                            snippet_content = "\n".join(lines[start_idx:end_idx])
                            snippets.append(CodeSnippet(
                                start_line=current_start,
                                end_line=current_end,
                                content=snippet_content
                            ))
                        current_start = None
                    else:
                        if not fallback_used:
                            logger.warning(f"Invalid END_LINE '{end_val}' in snippet response, including full file as snippet.")
                            snippets.append(CodeSnippet(
                                start_line=1,
                                end_line=len(lines),
                                content="\n".join(lines)
                            ))
                            fallback_used = True
                        current_start = None
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing snippet response: {e}. Response: {response_text}")

        return snippets
    
    def _build_discovery_prompt(self, request: ContextDiscoveryRequest, parsed_log: ParsedLogEntry) -> str:
        """Build prompt for context discovery"""
        
        prompt_parts = [
            "# Context Discovery for Error Analysis",
            "",
            "You are helping to discover relevant code files for analyzing an error log.",
            "Your goal is to identify which files would provide the most valuable context for understanding and diagnosing the error.",
            "",
            "## Error Information",
            f"**Error Message:** {request.error_message}",
            ""
        ]
        
        # Add log level and source information
        if parsed_log.level:
            prompt_parts.append(f"**Log Level:** {parsed_log.level}")
        if parsed_log.source:
            prompt_parts.append(f"**Source:** {parsed_log.source}")
        if parsed_log.service_name:
            prompt_parts.append(f"**Service:** {parsed_log.service_name}")
        if parsed_log.timestamp:
            prompt_parts.append(f"**Timestamp:** {parsed_log.timestamp}")
        
        prompt_parts.append("")
        
        # Add extracted error patterns
        if parsed_log.extracted_errors:
            prompt_parts.extend([
                "**Extracted Error Patterns:**",
                ""
            ])
            for i, error in enumerate(parsed_log.extracted_errors, 1):
                prompt_parts.append(f"{i}. {error}")
            prompt_parts.append("")
        
        if request.stack_trace:
            prompt_parts.extend([
                "**Stack Trace:**",
                "```",
                request.stack_trace,
                "```",
                ""
            ])
        
        # Add raw content if it contains additional structured information
        if isinstance(parsed_log.raw_content, dict) and parsed_log.raw_content:
            # Extract additional useful fields from structured logs
            additional_info = []
            
            # Look for common error-related fields
            error_fields = ['error_type', 'error_code', 'failed_operation', 'attempted_path', 
                          'exit_code', 'severity', 'component', 'module', 'function', 'line_number']
            
            for field in error_fields:
                if field in parsed_log.raw_content:
                    additional_info.append(f"- **{field.replace('_', ' ').title()}:** {parsed_log.raw_content[field]}")
            
            # Look for nested error details
            if 'error_details' in parsed_log.raw_content:
                error_details = parsed_log.raw_content['error_details']
                if isinstance(error_details, dict):
                    for key, value in error_details.items():
                        additional_info.append(f"- **{key.replace('_', ' ').title()}:** {value}")
            
            if additional_info:
                prompt_parts.extend([
                    "**Additional Error Details:**",
                    ""
                ])
                prompt_parts.extend(additional_info)
                prompt_parts.append("")
        
        prompt_parts.extend([
            "## Repository Structure",
            "```",
            request.file_structure,
            "```",
            ""
        ])
        
        if request.current_files:
            prompt_parts.extend([
                f"## Currently Analyzed Files ({len(request.current_files)})",
                ""
            ])
            for i, file_path in enumerate(request.current_files, 1):
                prompt_parts.append(f"{i}. {file_path}")
            prompt_parts.append("")
        
        if request.confidence_history:
            prompt_parts.extend([
                "## Confidence History",
                f"Previous confidence scores: {request.confidence_history}",
                f"Current iteration: {request.iteration}",
                ""
            ])
        
        prompt_parts.extend([
            "## Instructions",
            "",
            "Based on the error information and repository structure, please:",
            "",
            "1. **Identify 1-3 additional files** that would be most helpful for understanding this error",
            "2. **Provide reasoning** for why each file would be valuable",
            "3. **Assess confidence** in your ability to provide a full diagnosis with the current context (0.0-1.0 scale)",
            "",
            "Focus on files that are:",
            "- Mentioned in the stack trace or error message",
            "- Likely to contain the code that triggered the error",
            "- Configuration files that might affect the error",
            "- Recently modified files that could be related",
            "",
            "## Response Format",
            "",
            "**REQUESTED_FILES:**",
            "- path/to/file1.py - Reason for inclusion",
            "- path/to/file2.js - Reason for inclusion",
            "",
            "**REASONING:**",
            "Brief explanation of your file selection strategy and what additional context these files would provide.",
            "",
            "**DIAGNOSIS_CONFIDENCE:**",
            "0.85",
            "",
            "If no additional files are needed, respond with empty REQUESTED_FILES and a DIAGNOSIS_CONFIDENCE of 1.0."
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_discovery_response(self, response_text: str) -> ContextDiscoveryResponse:
        """Parse LLM response for context discovery"""
        
        # Initialize defaults
        requested_files = []
        reasoning = "No reasoning provided"
        confidence_score = 0.5
        
        lines = response_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("**REQUESTED_FILES:**"):
                current_section = "files"
                continue
            elif line.startswith("**REASONING:**"):
                current_section = "reasoning"
                continue
            elif line.startswith("**DIAGNOSIS_CONFIDENCE:**"):
                current_section = "confidence"
                continue
            
            if current_section == "files" and line.startswith("- "):
                # Extract file path
                file_info = line[2:].split(" - ")[0].strip()
                if file_info and not file_info.startswith("*"):
                    requested_files.append(file_info)
            
            elif current_section == "reasoning" and line and not line.startswith("**"):
                reasoning = line
                current_section = None  # Only take first line
            
            elif current_section == "confidence" and line:
                try:
                    confidence_score = float(line)
                    confidence_score = max(0.0, min(1.0, confidence_score))
                except ValueError:
                    pass
                current_section = None
            
        return ContextDiscoveryResponse(
            requested_files=requested_files,
            reasoning=reasoning,
            confidence_score=confidence_score
        )
    
    def _load_file_content(self, file_path: str, with_line_numbers: bool = True) -> Optional[FileContentInfo]:
        """Load file content with size limits and optionally with line numbers"""
        
        full_path = Path(self.config.repository.local_path) / file_path
        
        logger.debug(f"Loading file content: {file_path}")
        
        if not full_path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return None
            
        if not full_path.is_file():
            logger.warning(f"Path is not a file: {file_path}")
            return None
        
        try:
            size_bytes = full_path.stat().st_size
            size_kb = size_bytes / 1024
            
            logger.debug(f"File {file_path} size: {size_kb:.1f}KB")
            
            # Check size limit
            if size_kb > self.config.context_discovery.file_size_limit_kb:
                logger.warning(
                    f"File {file_path} too large ({size_kb:.1f}KB), skipping",
                    extra={
                        'file_path': file_path,
                        'file_size_kb': size_kb,
                        'size_limit_kb': self.config.context_discovery.file_size_limit_kb
                    }
                )
                return None
            
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            lines = content.splitlines()
            line_count = len(lines)

            if with_line_numbers:
                numbered_lines = [f"{i+1:4d} | {line}" for i, line in enumerate(lines)]
                content = '\n'.join(numbered_lines)

            file_info = FileContentInfo(
                file_path=file_path,
                size_kb=size_kb,
                content=content,
                snippets=[] # Snippets will be added later
            )
            
            logger.info(
                f"Successfully loaded file: {file_path}",
                extra={
                    'file_path': file_path,
                    'size_kb': round(size_kb, 2),
                    'line_count': line_count,
                    'content_length': len(content)
                }
            )
            
            return file_info
            
        except UnicodeDecodeError as e:
            logger.warning(f"Unicode decode error for file {file_path}: {e}")
            return None
        except PermissionError as e:
            logger.warning(f"Permission denied accessing file {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load file {file_path}: {e}")
            return None
    
    def _create_empty_result(self) -> ContextDiscoveryResult:
        """Create empty result when discovery is disabled"""
        return ContextDiscoveryResult(
            iterations_performed=0,
            files_analyzed=[],
            confidence_progression=[],
            total_context_size_kb=0.0,
            discovery_reasoning=["Context discovery disabled"],
            final_confidence=0.0
        )
    
    def get_context_files(self, discovery_result: ContextDiscoveryResult) -> List[FileContentInfo]:
        """Returns the discovered files with snippets."""
        logger.info(f"Returning {len(discovery_result.files_analyzed)} files with snippets.")
        return discovery_result.files_analyzed
