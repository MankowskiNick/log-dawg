"""
Logging framework for Log Dawg
"""
from .logger import LogDawgLogger, initialize_logging, get_logger, cleanup_logs, get_log_stats
from .diagnosis_logger import DiagnosisLogger
from .formatters import StructuredFormatter, DiagnosisFormatter
from .handlers import DiagnosisFileHandler, RotatingFileHandler

__all__ = [
    'LogDawgLogger',
    'DiagnosisLogger', 
    'StructuredFormatter',
    'DiagnosisFormatter',
    'DiagnosisFileHandler',
    'RotatingFileHandler',
    'initialize_logging',
    'get_logger',
    'cleanup_logs',
    'get_log_stats'
]
