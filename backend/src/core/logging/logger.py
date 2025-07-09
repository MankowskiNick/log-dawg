"""
Main logging configuration for Log Dawg
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from .formatters import StructuredFormatter
from .handlers import RotatingFileHandler


class LogDawgLogger:
    """Main logger configuration and management"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.log_dir = Path(config.get('log_directory', './logs'))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create system log directories
        (self.log_dir / 'system').mkdir(exist_ok=True)
        (self.log_dir / 'diagnoses').mkdir(exist_ok=True)
        
        self._loggers: Dict[str, logging.Logger] = {}
        self._setup_root_logger()
        self._setup_system_loggers()
    
    def _setup_root_logger(self):
        """Setup the root logger configuration"""
        root_logger = logging.getLogger('logdawg')
        root_logger.setLevel(getattr(logging, self.config.get('level', 'INFO')))
        
        # Clear any existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        if self.config.get('console_logging', True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, self.config.get('level', 'INFO')))
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # File handler for general application logs
        if self.config.get('file_logging', True):
            app_log_path = self.log_dir / 'system' / 'application.log'
            app_handler = RotatingFileHandler(
                str(app_log_path),
                maxBytes=self.config.get('max_log_size_mb', 50) * 1024 * 1024,
                backupCount=5
            )
            app_handler.setLevel(logging.DEBUG)
            
            if self.config.get('structured_format', True):
                app_formatter = StructuredFormatter()
            else:
                app_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            
            app_handler.setFormatter(app_formatter)
            root_logger.addHandler(app_handler)
        
        self._loggers['root'] = root_logger
    
    def _setup_system_loggers(self):
        """Setup specialized system loggers"""
        
        # API Logger
        api_logger = logging.getLogger('logdawg.api')
        api_logger.setLevel(logging.INFO)
        api_logger.propagate = False
        
        api_log_path = self.log_dir / 'system' / 'api.log'
        api_handler = RotatingFileHandler(
            str(api_log_path),
            maxBytes=self.config.get('max_log_size_mb', 50) * 1024 * 1024,
            backupCount=5
        )
        api_handler.setFormatter(StructuredFormatter())
        api_logger.addHandler(api_handler)
        
        self._loggers['api'] = api_logger
        
        # Health Logger
        health_logger = logging.getLogger('logdawg.health')
        health_logger.setLevel(logging.INFO)
        health_logger.propagate = False
        
        health_log_path = self.log_dir / 'system' / 'health.log'
        health_handler = RotatingFileHandler(
            str(health_log_path),
            maxBytes=self.config.get('max_log_size_mb', 50) * 1024 * 1024,
            backupCount=5
        )
        health_handler.setFormatter(StructuredFormatter())
        health_logger.addHandler(health_handler)
        
        self._loggers['health'] = health_logger
        
        # Performance Logger
        perf_logger = logging.getLogger('logdawg.performance')
        perf_logger.setLevel(logging.INFO)
        perf_logger.propagate = False
        
        perf_log_path = self.log_dir / 'system' / 'performance.log'
        perf_handler = RotatingFileHandler(
            str(perf_log_path),
            maxBytes=self.config.get('max_log_size_mb', 50) * 1024 * 1024,
            backupCount=5
        )
        perf_handler.setFormatter(StructuredFormatter())
        perf_logger.addHandler(perf_handler)
        
        self._loggers['performance'] = perf_logger
    
    def get_logger(self, name: str = 'root') -> logging.Logger:
        """Get a logger by name"""
        if name in self._loggers:
            return self._loggers[name]
        
        # Create a child logger if not found
        if name == 'root':
            return self._loggers['root']
        
        logger = logging.getLogger(f'logdawg.{name}')
        logger.setLevel(getattr(logging, self.config.get('level', 'INFO')))
        self._loggers[name] = logger
        
        return logger
    
    def cleanup_old_logs(self, retention_days: int = None):
        """Clean up old log files based on retention policy"""
        retention_days = retention_days or self.config.get('retention_days', 30)
        cutoff_time = datetime.now().timestamp() - (retention_days * 24 * 3600)
        
        # Clean up system logs
        system_log_dir = self.log_dir / 'system'
        for log_file in system_log_dir.glob('*.log*'):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    self.get_logger().info(f"Removed old log file: {log_file}")
                except Exception as e:
                    self.get_logger().error(f"Failed to remove old log file {log_file}: {e}")
        
        # Clean up diagnosis logs
        diagnoses_dir = self.log_dir / 'diagnoses'
        for date_dir in diagnoses_dir.iterdir():
            if date_dir.is_dir():
                if date_dir.stat().st_mtime < cutoff_time:
                    try:
                        import shutil
                        shutil.rmtree(date_dir)
                        self.get_logger().info(f"Removed old diagnosis log directory: {date_dir}")
                    except Exception as e:
                        self.get_logger().error(f"Failed to remove old diagnosis log directory {date_dir}: {e}")
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get statistics about log files"""
        stats = {
            'system_logs': {},
            'diagnosis_logs': {},
            'total_size_mb': 0
        }
        
        # System log stats
        system_log_dir = self.log_dir / 'system'
        if system_log_dir.exists():
            for log_file in system_log_dir.glob('*.log'):
                if log_file.is_file():
                    size_mb = log_file.stat().st_size / (1024 * 1024)
                    stats['system_logs'][log_file.name] = {
                        'size_mb': round(size_mb, 2),
                        'modified': datetime.fromtimestamp(log_file.stat().st_mtime)
                    }
                    stats['total_size_mb'] += size_mb
        
        # Diagnosis log stats
        diagnoses_dir = self.log_dir / 'diagnoses'
        if diagnoses_dir.exists():
            diagnosis_count = 0
            diagnosis_size = 0
            
            for date_dir in diagnoses_dir.iterdir():
                if date_dir.is_dir():
                    for diagnosis_dir in date_dir.iterdir():
                        if diagnosis_dir.is_dir():
                            diagnosis_count += 1
                            for log_file in diagnosis_dir.glob('*.log'):
                                if log_file.is_file():
                                    diagnosis_size += log_file.stat().st_size
            
            stats['diagnosis_logs'] = {
                'count': diagnosis_count,
                'size_mb': round(diagnosis_size / (1024 * 1024), 2)
            }
            stats['total_size_mb'] += diagnosis_size / (1024 * 1024)
        
        stats['total_size_mb'] = round(stats['total_size_mb'], 2)
        return stats


# Global logger instance
_logger_instance: Optional[LogDawgLogger] = None


def initialize_logging(config: Dict[str, Any]) -> LogDawgLogger:
    """Initialize the global logging configuration"""
    global _logger_instance
    _logger_instance = LogDawgLogger(config)
    return _logger_instance


def get_logger(name: str = 'root') -> logging.Logger:
    """Get a logger instance"""
    if _logger_instance is None:
        # Initialize with default config if not already initialized
        default_config = {
            'level': 'INFO',
            'log_directory': './logs',
            'console_logging': True,
            'file_logging': True,
            'structured_format': True,
            'max_log_size_mb': 50,
            'retention_days': 30
        }
        initialize_logging(default_config)
    
    return _logger_instance.get_logger(name)


def cleanup_logs(retention_days: int = None):
    """Clean up old log files"""
    if _logger_instance:
        _logger_instance.cleanup_old_logs(retention_days)


def get_log_stats() -> Dict[str, Any]:
    """Get logging statistics"""
    if _logger_instance:
        return _logger_instance.get_log_stats()
    return {}
