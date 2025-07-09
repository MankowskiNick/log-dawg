"""
Custom logging formatters for Log Dawg
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

class StructuredFormatter(logging.Formatter):
    """JSON structured logging formatter"""
    
    def __init__(self):
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        
        # Base log structure
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add thread info if available
        if hasattr(record, 'thread') and record.thread:
            log_data['thread_id'] = record.thread
            log_data['thread_name'] = getattr(record, 'threadName', '')
        
        # Add process info if available
        if hasattr(record, 'process') and record.process:
            log_data['process_id'] = record.process
        
        # Add extra fields from LogRecord
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'message', 'exc_info', 'exc_text',
                          'stack_info']:
                extra_fields[key] = value
        
        if extra_fields:
            log_data.update(extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add stack info if present
        if record.stack_info:
            log_data['stack_info'] = record.stack_info
        
        return json.dumps(log_data, default=self._json_serializer)
    
    def _json_serializer(self, obj):
        """Handle non-serializable objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return str(obj)
        else:
            return str(obj)

class DiagnosisFormatter(logging.Formatter):
    """Specialized formatter for diagnosis logs"""
    
    def __init__(self):
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format diagnosis log record with rich context"""
        
        # Base diagnosis log structure
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat() + 'Z',
            'level': record.levelname,
            'message': record.getMessage()
        }
        
        # Add diagnosis-specific fields
        diagnosis_fields = [
            'diagnosis_id', 'step', 'category', 'duration_ms', 'correlation_id',
            'provider', 'model', 'prompt_tokens', 'completion_tokens', 'total_tokens',
            'git_commits_included', 'files_analyzed', 'confidence_score',
            'api_response_code', 'retry_count', 'error_type'
        ]
        
        for field in diagnosis_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)
        
        # Add metadata if present
        if hasattr(record, 'metadata') and record.metadata:
            log_data['metadata'] = record.metadata
        
        # Add performance metrics if present
        if hasattr(record, 'performance') and record.performance:
            log_data['performance'] = record.performance
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info)
            }
        
        return json.dumps(log_data, default=self._json_serializer)
    
    def _json_serializer(self, obj):
        """Handle non-serializable objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return str(obj)
        else:
            return str(obj)

class CompactFormatter(logging.Formatter):
    """Compact formatter for console output"""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
    
    def format(self, record: logging.LogRecord) -> str:
        """Format with compact output"""
        formatted = super().format(record)
        
        # Add diagnosis ID if present
        if hasattr(record, 'diagnosis_id'):
            formatted = f"[{record.diagnosis_id[:8]}] {formatted}"
        
        # Add step if present
        if hasattr(record, 'step'):
            formatted = f"{formatted} [{record.step}]"
        
        return formatted

class PerformanceFormatter(logging.Formatter):
    """Specialized formatter for performance logs"""
    
    def __init__(self):
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format performance log record"""
        
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat() + 'Z',
            'event': record.getMessage(),
            'duration_ms': getattr(record, 'duration_ms', None),
            'memory_mb': getattr(record, 'memory_mb', None),
            'cpu_percent': getattr(record, 'cpu_percent', None)
        }
        
        # Add diagnosis context if present
        if hasattr(record, 'diagnosis_id'):
            log_data['diagnosis_id'] = record.diagnosis_id
        
        if hasattr(record, 'step'):
            log_data['step'] = record.step
        
        # Add custom metrics if present
        if hasattr(record, 'metrics') and record.metrics:
            log_data['metrics'] = record.metrics
        
        return json.dumps(log_data, default=self._json_serializer)
    
    def _json_serializer(self, obj):
        """Handle non-serializable objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return str(obj)
