"""
Two-stage diagnosis orchestration logic
"""
import time
from typing import List, Optional
from src.models.schemas import ParsedLogEntry, DiagnosisResult, GitInfo, GitCommitInfo, ContextDiscoveryResult, IntermediateReport
from src.core.logging import DiagnosisLogger
from .providers import LLMProvider
from .prompts import ReportPromptBuilder, JsonFormattingPromptBuilder
from .parsers import JsonResponseParser, ReportResponseParser


class DiagnosisOrchestrator:
    """Orchestrates the two-stage diagnosis workflow"""
    
    def __init__(
        self,
        provider: LLMProvider,
        context_discovery,
        report_prompt_builder: ReportPromptBuilder,
        json_prompt_builder: JsonFormattingPromptBuilder,
        json_parser: JsonResponseParser,
        report_parser: ReportResponseParser,
        config,
        logger
    ):
        self.provider = provider
        self.context_discovery = context_discovery
        self.report_prompt_builder = report_prompt_builder
        self.json_prompt_builder = json_prompt_builder
        self.json_parser = json_parser
        self.report_parser = report_parser
        self.config = config
        self.logger = logger
    
    async def orchestrate_diagnosis(
        self,
        parsed_log: ParsedLogEntry,
        git_info: GitInfo,
        recent_commits: Optional[List[GitCommitInfo]] = None,
        diagnosis_id: Optional[str] = None
    ) -> DiagnosisResult:
        """Orchestrate the complete two-stage diagnosis process"""
        
        # Initialize logging if diagnosis_id is provided
        if diagnosis_id and self.config.logging.per_diagnosis_logging:
            logging_config = {
                'log_directory': self.config.logging.log_directory,
                'max_prompt_log_length': self.config.logging.llm_interaction_logging.max_prompt_log_length,
                'max_response_log_length': self.config.logging.llm_interaction_logging.max_response_log_length,
                'truncate_large_responses': self.config.logging.llm_interaction_logging.truncate_large_responses
            }
            
            with DiagnosisLogger(diagnosis_id, logging_config) as logger:
                # Context Discovery (with logging)
                context_discovery_result = None
                discovered_files = []
                if self.config.context_discovery.enabled:
                    context_discovery_result = await self.context_discovery.discover_context(
                        parsed_log, git_info, logger
                    )
                    discovered_files = self.context_discovery.get_context_files(context_discovery_result)

                result = await self._perform_two_stage_diagnosis_with_logging(
                    parsed_log, git_info, recent_commits, logger, discovered_files, context_discovery_result
                )
                if result is None:
                    logger.log_error("Diagnosis result is None")
                    raise ValueError("Diagnosis result is None")
                return result
        else:
            # Fallback to non-logged diagnosis
            # Context Discovery (run for all paths)
            context_discovery_result = None
            discovered_files = []
            if self.config.context_discovery.enabled:
                context_discovery_result = await self.context_discovery.discover_context(
                    parsed_log, git_info, None # No logger here
                )
                discovered_files = self.context_discovery.get_context_files(context_discovery_result)
            
            return await self._perform_two_stage_diagnosis(
                parsed_log, git_info, recent_commits, discovered_files, context_discovery_result, diagnosis_id
            )
    
    async def _perform_two_stage_diagnosis(
        self,
        parsed_log: ParsedLogEntry,
        git_info: GitInfo,
        recent_commits: List[GitCommitInfo],
        discovered_files: List,
        context_discovery_result: Optional[ContextDiscoveryResult],
        diagnosis_id: Optional[str] = None
    ) -> DiagnosisResult:
        """Perform two-stage diagnosis without comprehensive logging"""
        
        try:
            self.logger.info(f"[{diagnosis_id}] Starting Stage 1: Narrative report generation")
            
            # Stage 1: Generate narrative report
            intermediate_report = await self._generate_narrative_report(
                parsed_log, git_info, recent_commits, discovered_files, diagnosis_id
            )
            
            self.logger.info(f"[{diagnosis_id}] Stage 1 completed, starting Stage 2: JSON formatting")
            
            # Stage 2: Convert to structured JSON
            diagnosis_result = await self._format_to_json(
                intermediate_report, parsed_log, git_info, recent_commits, discovered_files, context_discovery_result, diagnosis_id
            )
            
            # Add context discovery result to diagnosis
            if context_discovery_result:
                diagnosis_result.context_discovery = context_discovery_result
            
            self.logger.info(f"[{diagnosis_id}] Two-stage diagnosis completed successfully")
            return diagnosis_result
            
        except Exception as e:
            self.logger.error(f"[{diagnosis_id}] Two-stage diagnosis failed: {e}")
            return self._create_fallback_diagnosis(parsed_log, str(e))
    
    async def _perform_two_stage_diagnosis_with_logging(
        self,
        parsed_log: ParsedLogEntry,
        git_info: GitInfo,
        recent_commits: List[GitCommitInfo],
        logger: DiagnosisLogger,
        discovered_files: List,
        context_discovery_result: Optional[ContextDiscoveryResult]
    ) -> DiagnosisResult:
        """Perform two-stage diagnosis with comprehensive logging"""
        
        try:
            # Log initial context
            logger.log_info(
                "Starting two-stage log diagnosis",
                metadata={
                    'log_level': parsed_log.level,
                    'log_source': parsed_log.source,
                    'service_name': parsed_log.service_name,
                    'has_stack_trace': bool(parsed_log.stack_trace),
                    'error_patterns_count': len(parsed_log.extracted_errors),
                    'git_branch': git_info.branch,
                    'git_commits_count': len(git_info.recent_commits),
                    'recent_commits_count': len(recent_commits) if recent_commits else 0,
                    'context_files_discovered': len(discovered_files)
                }
            )
            
            # Stage 1: Generate narrative report
            with logger.log_step("stage1_narrative_report"):
                intermediate_report = await self._generate_narrative_report_with_logging(
                    parsed_log, git_info, recent_commits, discovered_files, logger
                )
            
            # Stage 2: Convert to structured JSON
            with logger.log_step("stage2_json_formatting"):
                diagnosis_result = await self._format_to_json_with_logging(
                    intermediate_report, parsed_log, git_info, recent_commits, discovered_files, context_discovery_result, logger
                )
            
            # Add context discovery result to diagnosis
            if context_discovery_result:
                diagnosis_result.context_discovery = context_discovery_result
            
            logger.log_info(
                "Successfully completed two-stage diagnosis",
                metadata={
                    'stage1_quality_score': intermediate_report['analysis_quality_score'],
                    'stage1_response_length': intermediate_report['stage1_metadata']['response_length'],
                    'final_confidence_score': diagnosis_result.confidence_score,
                    'recommendations_count': len(diagnosis_result.recommendations),
                    'relevant_files_count': len(diagnosis_result.relevant_code_files)
                }
            )
            
            return diagnosis_result
            
        except Exception as e:
            logger.log_error(
                f"Two-stage diagnosis failed: {str(e)}",
                error_type=type(e).__name__,
                exception_info=(type(e), e, e.__traceback__),
                metadata={
                    'step': logger.current_step,
                    'provider': self.config.llm.provider,
                    'model': self.config.llm.model
                }
            )
            
            # Return fallback diagnosis
            return self._create_fallback_diagnosis(parsed_log, str(e))
    
    async def _generate_narrative_report(
        self,
        parsed_log: ParsedLogEntry,
        git_info: GitInfo,
        recent_commits: List[GitCommitInfo],
        discovered_files: List,
        diagnosis_id: Optional[str] = None
    ) -> dict:
        """Generate Stage 1 narrative report"""
        
        # Build narrative analysis prompt
        prompt = self.report_prompt_builder.build_prompt(
            parsed_log, git_info, recent_commits, discovered_files
        )
        
        self.logger.info(f"[{diagnosis_id}] Stage 1 prompt built ({len(prompt)} chars)")
        
        try:
            # Send to LLM for narrative analysis
            self.logger.info(f"[{diagnosis_id}] Sending Stage 1 prompt to LLM provider")
            narrative_response = await self.provider.generate_diagnosis(prompt)
            self.logger.info(f"[{diagnosis_id}] Stage 1 LLM response received ({len(narrative_response)} chars)")
            
            # Parse narrative response
            intermediate_report = self.report_parser.parse_response(narrative_response, parsed_log)
            self.logger.info(f"[{diagnosis_id}] Stage 1 parsing completed, quality score: {intermediate_report['analysis_quality_score']:.2f}")
            
            return intermediate_report
            
        except Exception as e:
            self.logger.error(f"[{diagnosis_id}] Stage 1 failed: {e}")
            # Create fallback report
            return self.report_parser._create_fallback_report(parsed_log, str(e))
    
    async def _generate_narrative_report_with_logging(
        self,
        parsed_log: ParsedLogEntry,
        git_info: GitInfo,
        recent_commits: List[GitCommitInfo],
        discovered_files: List,
        logger: DiagnosisLogger
    ) -> dict:
        """Generate Stage 1 narrative report with logging"""
        
        # Build narrative analysis prompt
        with logger.log_step("build_stage1_prompt"):
            prompt = self.report_prompt_builder.build_prompt(
                parsed_log, git_info, recent_commits, discovered_files
            )
            logger.log_debug(
                f"Built Stage 1 narrative prompt with {len(prompt)} characters",
                metadata={
                    'prompt_length': len(prompt),
                    'context_files_included': len(discovered_files)
                }
            )
        
        # Send LLM request for Stage 1
        with logger.log_step("stage1_llm_request"):
            request_id = logger.log_llm_request(
                provider=self.config.llm.provider,
                model=self.config.llm.model,
                prompt=prompt,
                metadata={
                    'stage': 1,
                    'purpose': 'narrative_analysis',
                    'max_tokens': self.config.llm.max_tokens,
                    'temperature': self.config.llm.temperature
                }
            )
            
            # Time the LLM request
            start_time = time.time()
            try:
                narrative_response = await self.provider.generate_diagnosis(prompt)
                response_time_ms = (time.time() - start_time) * 1000
                
                logger.log_llm_response(
                    request_id=request_id,
                    response=narrative_response,
                    token_usage=None,  # Would need provider-specific implementation
                    response_time_ms=response_time_ms,
                    metadata={
                        'stage': 1,
                        'response_length': len(narrative_response),
                        'provider_model': f"{self.config.llm.provider}:{self.config.llm.model}"
                    }
                )
                
            except Exception as e:
                response_time_ms = (time.time() - start_time) * 1000
                logger.log_llm_error(
                    request_id=request_id,
                    error=e,
                    metadata={
                        'stage': 1,
                        'response_time_ms': response_time_ms,
                        'provider_model': f"{self.config.llm.provider}:{self.config.llm.model}"
                    }
                )
                raise
        
        # Parse Stage 1 response
        with logger.log_step("parse_stage1_response"):
            intermediate_report = self.report_parser.parse_response(narrative_response, parsed_log)
            
            logger.log_info(
                "Successfully parsed Stage 1 narrative response",
                metadata={
                    'quality_score': intermediate_report['analysis_quality_score'],
                    'key_findings_count': len(intermediate_report['key_findings']),
                    'response_length': intermediate_report['stage1_metadata']['response_length'],
                    'has_code_references': intermediate_report['stage1_metadata']['has_code_references'],
                    'has_recommendations': intermediate_report['stage1_metadata']['has_recommendations']
                }
            )
        
        return intermediate_report
    
    async def _format_to_json(
        self,
        intermediate_report: dict,
        parsed_log: ParsedLogEntry,
        git_info: GitInfo,
        recent_commits: List[GitCommitInfo],
        discovered_files: List,
        context_discovery_result: Optional[ContextDiscoveryResult],
        diagnosis_id: Optional[str] = None
    ) -> DiagnosisResult:
        """Convert Stage 1 report to structured JSON format"""
        
        # Build JSON formatting prompt
        prompt = self.json_prompt_builder.build_prompt(
            intermediate_report['content'], parsed_log, git_info, recent_commits, discovered_files
        )
        
        self.logger.info(f"[{diagnosis_id}] Stage 2 prompt built ({len(prompt)} chars)")
        
        try:
            # Send to LLM for JSON formatting
            self.logger.info(f"[{diagnosis_id}] Sending Stage 2 prompt to LLM provider")
            json_response = await self.provider.generate_diagnosis(prompt)
            self.logger.info(f"[{diagnosis_id}] Stage 2 LLM response received ({len(json_response)} chars)")
            
            # Parse JSON response with repair capabilities
            diagnosis_result = self.json_parser.parse_response_with_repair(
                json_response, parsed_log, context_discovery_result
            )
            self.logger.info(f"[{diagnosis_id}] Stage 2 parsing completed, confidence: {diagnosis_result.confidence_score:.2f}")
            
            return diagnosis_result
            
        except Exception as e:
            self.logger.error(f"[{diagnosis_id}] Stage 2 failed: {e}")
            return self.json_parser._create_fallback_diagnosis(parsed_log, str(e))
    
    async def _format_to_json_with_logging(
        self,
        intermediate_report: dict,
        parsed_log: ParsedLogEntry,
        git_info: GitInfo,
        recent_commits: List[GitCommitInfo],
        discovered_files: List,
        context_discovery_result: Optional[ContextDiscoveryResult],
        logger: DiagnosisLogger
    ) -> DiagnosisResult:
        """Convert Stage 1 report to structured JSON format with logging"""
        
        # Build JSON formatting prompt
        with logger.log_step("build_stage2_prompt"):
            prompt = self.json_prompt_builder.build_prompt(
                intermediate_report['content'], parsed_log, git_info, recent_commits, discovered_files
            )
            logger.log_debug(
                f"Built Stage 2 JSON formatting prompt with {len(prompt)} characters",
                metadata={
                    'prompt_length': len(prompt),
                    'stage1_report_length': len(intermediate_report['content'])
                }
            )
        
        # Send LLM request for Stage 2
        with logger.log_step("stage2_llm_request"):
            request_id = logger.log_llm_request(
                provider=self.config.llm.provider,
                model=self.config.llm.model,
                prompt=prompt,
                metadata={
                    'stage': 2,
                    'purpose': 'json_formatting',
                    'max_tokens': self.config.llm.max_tokens,
                    'temperature': self.config.llm.temperature
                }
            )
            
            # Time the LLM request
            start_time = time.time()
            try:
                json_response = await self.provider.generate_diagnosis(prompt)
                response_time_ms = (time.time() - start_time) * 1000
                
                logger.log_llm_response(
                    request_id=request_id,
                    response=json_response,
                    token_usage=None,  # Would need provider-specific implementation
                    response_time_ms=response_time_ms,
                    metadata={
                        'stage': 2,
                        'response_length': len(json_response),
                        'provider_model': f"{self.config.llm.provider}:{self.config.llm.model}"
                    }
                )
                
            except Exception as e:
                response_time_ms = (time.time() - start_time) * 1000
                logger.log_llm_error(
                    request_id=request_id,
                    error=e,
                    metadata={
                        'stage': 2,
                        'response_time_ms': response_time_ms,
                        'provider_model': f"{self.config.llm.provider}:{self.config.llm.model}"
                    }
                )
                raise
        
        # Parse Stage 2 response
        with logger.log_step("parse_stage2_response"):
            diagnosis_result = self.json_parser.parse_response_with_repair(
                json_response, parsed_log, context_discovery_result
            )
            
            logger.log_info(
                "Successfully parsed Stage 2 JSON response",
                metadata={
                    'confidence_score': diagnosis_result.confidence_score,
                    'recommendations_count': len(diagnosis_result.recommendations),
                    'relevant_files_count': len(diagnosis_result.relevant_code_files),
                    'error_type': diagnosis_result.error_type,
                    'title_length': len(diagnosis_result.title)
                }
            )
        
        return diagnosis_result
    
    def _create_fallback_diagnosis(self, parsed_log: ParsedLogEntry, error: str) -> DiagnosisResult:
        """Create fallback diagnosis when both stages fail"""
        # Generate fallback title
        title = f"{parsed_log.level.title()} Level Issue"
        if parsed_log.service_name:
            title = f"{title} in {parsed_log.service_name}"
        
        return DiagnosisResult(
            title=title,
            error_type="Runtime Error",
            summary=f"Error log detected: {parsed_log.level} level issue",
            root_cause=f"Two-stage analysis failed due to error: {error}",
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
