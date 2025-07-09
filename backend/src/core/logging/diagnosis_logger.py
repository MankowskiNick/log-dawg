"""
Per-diagnosis logging functionality for Log Dawg
"""
import logging
import time
import psutil
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from .formatters import DiagnosisFormatter, PerformanceFormatter
from .handlers import BufferedDiagnosisHandler, DiagnosisFileHandler

class DiagnosisLogger:
    """Context manager for per-diagnosis logging"""
    
    def __init__(self, diagnosis_id: str, config: Dict[str, Any] = None):
        self.diagnosis_id = diagnosis_id
        self.config = config or {}
        self.log_dir = Path(self.config.get('log_directory', './logs'))
        
        # Initialize loggers
        self._setup_loggers()
        
        # Track performance metrics
        self.start_time = None
        self.step_timings = {}
        self.current_step = None
        self.process = psutil.Process()
        
        # Track LLM interactions
        self.llm_calls = []
        
        # Track errors
        self.errors = []
    
    def _setup_loggers(self):
        """Setup diagnosis-specific loggers"""
        self.loggers = {}
        
        # Main execution logger
        exec_logger = logging.getLogger(f'logdawg.diagnosis.{self.diagnosis_id}.execution')
        exec_logger.setLevel(logging.DEBUG)
        exec_logger.propagate = False
        
        exec_handler = DiagnosisFileHandler(self.diagnosis_id, 'execution', str(self.log_dir))
        exec_handler.setFormatter(DiagnosisFormatter())
        exec_logger.addHandler(exec_handler)
        
        self.loggers['execution'] = exec_logger
        
        # LLM interactions logger
        llm_logger = logging.getLogger(f'logdawg.diagnosis.{self.diagnosis_id }.llm_interactions')
        llm_logger.setLevel(logging.DEBUG)
        llm_logger.propagate = False
        
        llm_handler = DiagnosisFileHandler(self.diagnosis_id, 'llm_interactions', str(self.log_dir))
        llm_handler.setFormatter(DiagnosisFormatter())
        llm_logger.addHandler(llm_handler)
        
        self.loggers['llm'] = llm_logger
        
        # Git operations logger
        git_logger = logging.getLogger(f'logdawg.diagnosis.{self.diagnosis_id}.git_operations')
        git_logger.setLevel(logging.DEBUG)
        git_logger.propagate = False
        
        git_handler = DiagnosisFileHandler(self.diagnosis_id, 'git_operations', str(self.log_dir))
        git_handler.setFormatter(DiagnosisFormatter())
        git_logger.addHandler(git_handler)
        
        self.loggers['git'] = git_logger
        
        # Performance logger
        perf_logger = logging.getLogger(f'logdawg.diagnosis.{self.diagnosis_id}.performance')
        perf_logger.setLevel(logging.INFO)
        perf_logger.propagate = False
        
        perf_handler = DiagnosisFileHandler(self.diagnosis_id, 'performance', str(self.log_dir))
        perf_handler.setFormatter(PerformanceFormatter())
        perf_logger.addHandler(perf_handler)
        
        self.loggers['performance'] = perf_logger
        
        # Errors logger
        error_logger = logging.getLogger(f'logdawg.diagnosis.{self.diagnosis_id}.errors')
        error_logger.setLevel(logging.WARNING)
        error_logger.propagate = False
        
        error_handler = DiagnosisFileHandler(self.diagnosis_id, 'errors', str(self.log_dir))
        error_handler.setFormatter(DiagnosisFormatter())
        error_logger.addHandler(error_handler)
        
        self.loggers['errors'] = error_logger
    
    def __enter__(self):
        """Enter the diagnosis logging context"""
        self.start_time = time.time()
        
        # Log diagnosis start
        self.loggers['execution'].info(
            "Diagnosis started",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': 'diagnosis_start',
                'category': 'EXECUTION',
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'process_id': self.process.pid
                }
            }
        )
        
        # Record initial system state
        self._log_system_state('diagnosis_start')
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the diagnosis logging context"""
        end_time = time.time()
        total_duration = (end_time - self.start_time) * 1000  # Convert to milliseconds
        
        # Log any exception
        if exc_type:
            self.log_error(
                f"Diagnosis failed with {exc_type.__name__}: {exc_val}",
                error_type=exc_type.__name__,
                exception_info=(exc_type, exc_val, exc_tb)
            )
        
        # Log diagnosis completion
        self.loggers['execution'].info(
            "Diagnosis completed",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': 'diagnosis_complete',
                'category': 'EXECUTION',
                'duration_ms': total_duration,
                'metadata': {
                    'total_steps': len(self.step_timings),
                    'llm_calls': len(self.llm_calls),
                    'errors': len(self.errors),
                    'success': exc_type is None
                }
            }
        )
        
        # Log final performance summary
        self._log_performance_summary(total_duration)
        
        # Close all handlers
        self._close_handlers()
    
    def log_step_start(self, step_name: str, metadata: Dict[str, Any] = None):
        """Log the start of a processing step"""
        self.current_step = step_name
        self.step_timings[step_name] = {'start': time.time()}
        
        self.loggers['execution'].info(
            f"Starting step: {step_name}",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': step_name,
                'category': 'EXECUTION',
                'metadata': metadata or {}
            }
        )
    
    def log_step_end(self, step_name: str = None, metadata: Dict[str, Any] = None):
        """Log the end of a processing step"""
        step_name = step_name or self.current_step
        
        if step_name and step_name in self.step_timings:
            end_time = time.time()
            duration = (end_time - self.step_timings[step_name]['start']) * 1000
            self.step_timings[step_name]['end'] = end_time
            self.step_timings[step_name]['duration_ms'] = duration
            
            self.loggers['execution'].info(
                f"Completed step: {step_name}",
                extra={
                    'diagnosis_id': self.diagnosis_id,
                    'step': step_name,
                    'category': 'EXECUTION',
                    'duration_ms': duration,
                    'metadata': metadata or {}
                }
            )
            
            # Log to performance logger
            self.loggers['performance'].info(
                f"Step performance: {step_name}",
                extra={
                    'diagnosis_id': self.diagnosis_id,
                    'step': step_name,
                    'duration_ms': duration,
                    'memory_mb': self._get_memory_usage(),
                    'cpu_percent': self._get_cpu_usage()
                }
            )
        
        if step_name == self.current_step:
            self.current_step = None
    
    @contextmanager
    def log_step(self, step_name: str, metadata: Dict[str, Any] = None):
        """Context manager for logging a step"""
        self.log_step_start(step_name, metadata)
        try:
            yield
        finally:
            self.log_step_end(step_name)
    
    def log_llm_request(self, provider: str, model: str, prompt: str, 
                       metadata: Dict[str, Any] = None):
        """Log an LLM request"""
        request_id = f"req_{len(self.llm_calls) + 1}"
        
        # Truncate prompt if configured to do so
        max_prompt_length = self.config.get('max_prompt_log_length', 50000)
        truncate_enabled = self.config.get('truncate_large_responses', True)
        
        logged_prompt = prompt
        if truncate_enabled and len(prompt) > max_prompt_length:
            logged_prompt = prompt[:max_prompt_length]
            logged_prompt += f"... (truncated, original length: {len(prompt)})"
        
        request_data = {
            'request_id': request_id,
            'provider': provider,
            'model': model,
            'prompt_length': len(prompt),
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        self.llm_calls.append(request_data)
        
        self.loggers['llm'].info(
            f"LLM request sent to {provider}",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'LLM_REQUEST',
                'provider': provider,
                'model': model,
                'prompt_tokens': len(prompt.split()) if prompt else 0,
                'metadata': {
                    'request_id': request_id,
                    'prompt': logged_prompt,
                    **request_data['metadata']
                }
            }
        )
        
        return request_id
    
    def log_llm_response(self, request_id: str, response: str, 
                        token_usage: Dict[str, int] = None,
                        response_time_ms: float = None,
                        metadata: Dict[str, Any] = None):
        """Log an LLM response"""
        # Find the corresponding request
        request_data = None
        for call in self.llm_calls:
            if call.get('request_id') == request_id:
                request_data = call
                break
        
        # Truncate response if configured to do so
        max_response_length = self.config.get('max_response_log_length', 50000)
        truncate_enabled = self.config.get('truncate_large_responses', True)
        
        logged_response = response if response else ""
        if truncate_enabled and response and len(response) > max_response_length:
            logged_response = response[:max_response_length]
            logged_response += f"... (truncated, original length: {len(response)})"
        
        log_metadata = {
            'request_id': request_id,
            'response': logged_response,
            'response_length': len(response) if response else 0,
            'response_time_ms': response_time_ms,
            **(metadata or {})
        }
        
        if token_usage:
            log_metadata.update(token_usage)
        
        self.loggers['llm'].info(
            f"LLM response received",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'LLM_RESPONSE',
                'duration_ms': response_time_ms,
                'prompt_tokens': token_usage.get('prompt_tokens') if token_usage else None,
                'completion_tokens': token_usage.get('completion_tokens') if token_usage else None,
                'total_tokens': token_usage.get('total_tokens') if token_usage else None,
                'metadata': log_metadata
            }
        )
        
        # Update the request data
        if request_data:
            request_data.update({
                'response_received': datetime.now().isoformat(),
                'response_time_ms': response_time_ms,
                'token_usage': token_usage or {},
                'response_length': len(response) if response else 0
            })
    
    def log_llm_error(self, request_id: str, error: Exception, 
                     retry_count: int = 0, metadata: Dict[str, Any] = None):
        """Log an LLM error"""
        error_data = {
            'request_id': request_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'retry_count': retry_count,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        self.errors.append(error_data)
        
        self.loggers['llm'].error(
            f"LLM request failed: {error}",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'LLM_ERROR',
                'error_type': type(error).__name__,
                'retry_count': retry_count,
                'metadata': error_data
            },
            exc_info=True
        )
    
    def log_git_operation(self, operation: str, result: Dict[str, Any],
                         duration_ms: float = None):
        """Log a git operation"""
        self.loggers['git'].info(
            f"Git operation: {operation}",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'GIT_OPERATION',
                'duration_ms': duration_ms,
                'metadata': {
                    'operation': operation,
                    'result': result
                }
            }
        )
    
    def log_error(self, message: str, error_type: str = None, 
                 exception_info: tuple = None, metadata: Dict[str, Any] = None):
        """Log an error"""
        error_data = {
            'message': message,
            'error_type': error_type,
            'timestamp': datetime.now().isoformat(),
            'step': self.current_step,
            'metadata': metadata or {}
        }
        
        self.errors.append(error_data)
        
        self.loggers['errors'].error(
            message,
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'ERROR',
                'error_type': error_type,
                'metadata': error_data
            },
            exc_info=exception_info
        )
    
    def log_info(self, message: str, step: str = None, 
                metadata: Dict[str, Any] = None):
        """Log general information"""
        self.loggers['execution'].info(
            message,
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': step or self.current_step,
                'category': 'INFO',
                'metadata': metadata or {}
            }
        )
    
    def log_debug(self, message: str, step: str = None,
                 metadata: Dict[str, Any] = None):
        """Log debug information"""
        self.loggers['execution'].debug(
            message,
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': step or self.current_step,
                'category': 'DEBUG',
                'metadata': metadata or {}
            }
        )
    
    def log_context_discovery_start(self, metadata: Dict[str, Any] = None):
        """Log the start of context discovery process"""
        self.loggers['execution'].info(
            "Context discovery process started",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'CONTEXT_DISCOVERY_START',
                'metadata': metadata or {}
            }
        )
    
    def log_context_discovery_iteration_start(self, iteration: int, metadata: Dict[str, Any] = None):
        """Log the start of a context discovery iteration"""
        self.loggers['execution'].info(
            f"Context discovery iteration {iteration} started",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'CONTEXT_DISCOVERY_ITERATION_START',
                'iteration': iteration,
                'metadata': metadata or {}
            }
        )
    
    def log_context_discovery_iteration_end(self, iteration: int, result: Dict[str, Any], metadata: Dict[str, Any] = None):
        """Log the end of a context discovery iteration"""
        self.loggers['execution'].info(
            f"Context discovery iteration {iteration} completed",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'CONTEXT_DISCOVERY_ITERATION_END',
                'iteration': iteration,
                'result': result,
                'metadata': metadata or {}
            }
        )
    
    def log_file_selection_decision(self, file_path: str, decision: str, reasoning: str, score: float = None, metadata: Dict[str, Any] = None):
        """Log file selection decisions with reasoning"""
        self.loggers['execution'].info(
            f"File selection decision: {decision} for {file_path}",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'FILE_SELECTION_DECISION',
                'file_path': file_path,
                'decision': decision,
                'reasoning': reasoning,
                'score': score,
                'metadata': metadata or {}
            }
        )
    
    def log_context_sufficiency_check(self, iteration: int, should_continue: bool, reason: str, context_metrics: Dict[str, Any], metadata: Dict[str, Any] = None):
        """Log context sufficiency evaluation"""
        self.loggers['execution'].info(
            f"Context sufficiency check (iteration {iteration}): {'Continue' if should_continue else 'Stop'} - {reason}",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'CONTEXT_SUFFICIENCY_CHECK',
                'iteration': iteration,
                'should_continue': should_continue,
                'reason': reason,
                'context_metrics': context_metrics,
                'metadata': metadata or {}
            }
        )
    
    def log_confidence_progression(self, iteration: int, confidence_score: float, previous_score: float = None, reasoning: str = None, metadata: Dict[str, Any] = None):
        """Log confidence score progression"""
        improvement = confidence_score - previous_score if previous_score is not None else None
        
        self.loggers['execution'].info(
            f"Confidence progression (iteration {iteration}): {confidence_score:.3f}" + 
            (f" (Δ{improvement:+.3f})" if improvement is not None else ""),
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'CONFIDENCE_PROGRESSION',
                'iteration': iteration,
                'confidence_score': confidence_score,
                'previous_score': previous_score,
                'improvement': improvement,
                'reasoning': reasoning,
                'metadata': metadata or {}
            }
        )
    
    def log_context_discovery_summary(self, summary: Dict[str, Any], metadata: Dict[str, Any] = None):
        """Log final context discovery summary"""
        self.loggers['execution'].info(
            f"Context discovery completed: {summary.get('iterations', 0)} iterations, " +
            f"{summary.get('files_count', 0)} files, {summary.get('total_size_kb', 0):.1f}KB, " +
            f"final confidence: {summary.get('final_confidence', 0):.3f}",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'CONTEXT_DISCOVERY_SUMMARY',
                'summary': summary,
                'metadata': metadata or {}
            }
        )
    
    def log_file_analysis_start(self, file_path: str, analysis_type: str, metadata: Dict[str, Any] = None):
        """Log the start of file analysis"""
        self.loggers['execution'].info(
            f"Starting {analysis_type} analysis for file: {file_path}",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'FILE_ANALYSIS_START',
                'file_path': file_path,
                'analysis_type': analysis_type,
                'metadata': metadata or {}
            }
        )
    
    def log_file_analysis_result(self, file_path: str, analysis_type: str, result: Dict[str, Any], metadata: Dict[str, Any] = None):
        """Log file analysis results"""
        self.loggers['execution'].info(
            f"Completed {analysis_type} analysis for file: {file_path}",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'FILE_ANALYSIS_RESULT',
                'file_path': file_path,
                'analysis_type': analysis_type,
                'result': result,
                'metadata': metadata or {}
            }
        )
    
    def log_repository_scan_start(self, scan_type: str, parameters: Dict[str, Any] = None, metadata: Dict[str, Any] = None):
        """Log the start of repository scanning"""
        self.loggers['execution'].info(
            f"Starting repository scan: {scan_type}",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'REPOSITORY_SCAN_START',
                'scan_type': scan_type,
                'parameters': parameters or {},
                'metadata': metadata or {}
            }
        )
    
    def log_repository_scan_result(self, scan_type: str, result: Dict[str, Any], metadata: Dict[str, Any] = None):
        """Log repository scan results"""
        self.loggers['execution'].info(
            f"Completed repository scan: {scan_type}",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'REPOSITORY_SCAN_RESULT',
                'scan_type': scan_type,
                'result': result,
                'metadata': metadata or {}
            }
        )
    
    def log_file_scoring_decision(self, file_path: str, score_breakdown: Dict[str, float], total_score: float, reasoning: str, metadata: Dict[str, Any] = None):
        """Log detailed file scoring decisions"""
        self.loggers['execution'].debug(
            f"File scoring decision for {file_path}: {total_score:.3f}",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'FILE_SCORING_DECISION',
                'file_path': file_path,
                'total_score': total_score,
                'score_breakdown': score_breakdown,
                'reasoning': reasoning,
                'metadata': metadata or {}
            }
        )
    
    def log_discovery_prompt_generation(self, iteration: int, prompt_length: int, context_info: Dict[str, Any], metadata: Dict[str, Any] = None):
        """Log context discovery prompt generation"""
        self.loggers['execution'].debug(
            f"Generated discovery prompt for iteration {iteration}",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'DISCOVERY_PROMPT_GENERATION',
                'iteration': iteration,
                'prompt_length': prompt_length,
                'context_info': context_info,
                'metadata': metadata or {}
            }
        )
    
    def log_discovery_response_parsing(self, iteration: int, response_length: int, parsed_result: Dict[str, Any], metadata: Dict[str, Any] = None):
        """Log context discovery response parsing"""
        self.loggers['execution'].debug(
            f"Parsed discovery response for iteration {iteration}",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'DISCOVERY_RESPONSE_PARSING',
                'iteration': iteration,
                'response_length': response_length,
                'parsed_result': parsed_result,
                'metadata': metadata or {}
            }
        )
    
    def log_context_validation_check(self, validation_type: str, check_result: bool, details: Dict[str, Any], metadata: Dict[str, Any] = None):
        """Log context validation checks"""
        self.loggers['execution'].debug(
            f"Context validation check ({validation_type}): {'PASS' if check_result else 'FAIL'}",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'step': self.current_step,
                'category': 'CONTEXT_VALIDATION_CHECK',
                'validation_type': validation_type,
                'check_result': check_result,
                'details': details,
                'metadata': metadata or {}
            }
        )
    
    def _log_system_state(self, event: str):
        """Log current system state"""
        try:
            memory_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent()
            
            self.loggers['performance'].info(
                f"System state: {event}",
                extra={
                    'diagnosis_id': self.diagnosis_id,
                    'memory_mb': memory_info.rss / (1024 * 1024),
                    'cpu_percent': cpu_percent,
                    'metrics': {
                        'memory_rss_mb': memory_info.rss / (1024 * 1024),
                        'memory_vms_mb': memory_info.vms / (1024 * 1024),
                        'cpu_percent': cpu_percent,
                        'num_threads': self.process.num_threads()
                    }
                }
            )
        except Exception as e:
            self.log_debug(f"Failed to log system state: {e}")
    
    def _log_performance_summary(self, total_duration_ms: float):
        """Log performance summary"""
        summary = {
            'total_duration_ms': total_duration_ms,
            'step_count': len(self.step_timings),
            'llm_calls': len(self.llm_calls),
            'error_count': len(self.errors),
            'step_breakdown': {
                step: data.get('duration_ms', 0)
                for step, data in self.step_timings.items()
            }
        }
        
        # Calculate LLM statistics
        if self.llm_calls:
            total_tokens = sum(
                call.get('token_usage', {}).get('total_tokens') or 0
                for call in self.llm_calls
            )
            total_llm_time = sum(
                call.get('response_time_ms') or 0
                for call in self.llm_calls
            )
            
            summary['llm_stats'] = {
                'total_calls': len(self.llm_calls),
                'total_tokens': total_tokens,
                'total_llm_time_ms': total_llm_time,
                'avg_tokens_per_call': total_tokens / len(self.llm_calls) if self.llm_calls else 0
            }
        
        self.loggers['performance'].info(
            "Diagnosis performance summary",
            extra={
                'diagnosis_id': self.diagnosis_id,
                'metrics': summary
            }
        )
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            return self.process.memory_info().rss / (1024 * 1024)
        except:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            return self.process.cpu_percent()
        except:
            return 0.0
    
    def _close_handlers(self):
        """Close all logging handlers"""
        for logger in self.loggers.values():
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
