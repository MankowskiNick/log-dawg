"""
Custom logging handlers for Log Dawg
"""
import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

class RotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Enhanced rotating file handler with additional features"""
    
    def __init__(self, filename: str, mode: str = 'a', maxBytes: int = 0, 
                 backupCount: int = 0, encoding: Optional[str] = None, 
                 delay: bool = False, errors: Optional[str] = None):
        # Ensure directory exists
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay, errors)
    
    def emit(self, record: logging.LogRecord):
        """Emit a log record with error handling"""
        try:
            super().emit(record)
        except Exception:
            # If file writing fails, try to handle gracefully
            self.handleError(record)

class DiagnosisFileHandler(logging.FileHandler):
    """File handler for per-diagnosis logging"""
    
    def __init__(self, diagnosis_id: str, log_type: str, log_dir: str = './logs'):
        self.diagnosis_id = diagnosis_id
        self.log_type = log_type
        self.log_dir = Path(log_dir)
        
        # Create diagnosis-specific directory structure
        date_str = datetime.now().strftime('%Y-%m-%d')
        diagnosis_dir = self.log_dir / 'diagnoses' / date_str / f'diagnosis-{diagnosis_id}'
        diagnosis_dir.mkdir(parents=True, exist_ok=True)
        
        # Set the log file path
        log_file = diagnosis_dir / f'{log_type}.log'
        
        super().__init__(str(log_file), mode='a', encoding='utf-8', delay=False)
    
    def emit(self, record: logging.LogRecord):
        """Emit a log record with diagnosis context"""
        # Add diagnosis ID to record if not present
        if not hasattr(record, 'diagnosis_id'):
            record.diagnosis_id = self.diagnosis_id
        
        try:
            super().emit(record)
        except Exception:
            self.handleError(record)

class BufferedDiagnosisHandler(logging.Handler):
    """Buffered handler that flushes logs at the end of diagnosis"""
    
    def __init__(self, diagnosis_id: str, log_dir: str = './logs', capacity: int = 1000):
        super().__init__()
        self.diagnosis_id = diagnosis_id
        self.log_dir = Path(log_dir)
        self.capacity = capacity
        self.buffer = []
        self.handlers = {}
    
    def emit(self, record: logging.LogRecord):
        """Buffer the log record"""
        # Add diagnosis ID to record
        if not hasattr(record, 'diagnosis_id'):
            record.diagnosis_id = self.diagnosis_id
        
        self.buffer.append(record)
        
        # Flush if buffer is full
        if len(self.buffer) >= self.capacity:
            self.flush()
    
    def flush(self):
        """Flush all buffered records to appropriate files"""
        if not self.buffer:
            return
        
        # Group records by log type
        grouped_records = {}
        for record in self.buffer:
            log_type = getattr(record, 'category', 'general').lower()
            if log_type not in grouped_records:
                grouped_records[log_type] = []
            grouped_records[log_type].append(record)
        
        # Write each group to its respective file
        for log_type, records in grouped_records.items():
            handler = self._get_handler(log_type)
            for record in records:
                handler.emit(record)
            handler.flush()
        
        # Clear buffer
        self.buffer.clear()
    
    def _get_handler(self, log_type: str) -> DiagnosisFileHandler:
        """Get or create handler for specific log type"""
        if log_type not in self.handlers:
            self.handlers[log_type] = DiagnosisFileHandler(
                self.diagnosis_id, log_type, str(self.log_dir)
            )
            # Set the same formatter as this handler
            if self.formatter:
                self.handlers[log_type].setFormatter(self.formatter)
        
        return self.handlers[log_type]
    
    def close(self):
        """Close handler and flush remaining records"""
        self.flush()
        
        # Close all sub-handlers
        for handler in self.handlers.values():
            handler.close()
        
        super().close()

class TimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """Enhanced timed rotating file handler"""
    
    def __init__(self, filename: str, when: str = 'midnight', interval: int = 1,
                 backupCount: int = 0, encoding: Optional[str] = None,
                 delay: bool = False, utc: bool = False, atTime: Optional[datetime] = None):
        # Ensure directory exists
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc, atTime)
    
    def emit(self, record: logging.LogRecord):
        """Emit a log record with error handling"""
        try:
            super().emit(record)
        except Exception:
            self.handleError(record)

class JSONFileHandler(logging.FileHandler):
    """File handler that writes JSON logs"""
    
    def __init__(self, filename: str, mode: str = 'a', encoding: str = 'utf-8', delay: bool = False):
        # Ensure directory exists
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        
        super().__init__(filename, mode, encoding, delay)
    
    def emit(self, record: logging.LogRecord):
        """Emit a JSON formatted log record"""
        try:
            # Format the record
            formatted_record = self.format(record)
            
            # Write to file
            if self.stream is None:
                self.stream = self._open()
            
            self.stream.write(formatted_record + '\n')
            self.flush()
            
        except Exception:
            self.handleError(record)

class MultiFileHandler(logging.Handler):
    """Handler that writes to multiple files based on log level or category"""
    
    def __init__(self, base_path: str, split_by: str = 'level'):
        super().__init__()
        self.base_path = Path(base_path)
        self.split_by = split_by  # 'level' or 'category'
        self.handlers = {}
    
    def emit(self, record: logging.LogRecord):
        """Emit record to appropriate file based on splitting criteria"""
        try:
            # Determine the file key
            if self.split_by == 'level':
                file_key = record.levelname.lower()
            elif self.split_by == 'category':
                file_key = getattr(record, 'category', 'general').lower()
            else:
                file_key = 'default'
            
            # Get or create handler for this key
            handler = self._get_handler(file_key)
            handler.emit(record)
            
        except Exception:
            self.handleError(record)
    
    def _get_handler(self, file_key: str) -> logging.FileHandler:
        """Get or create handler for specific file"""
        if file_key not in self.handlers:
            file_path = self.base_path.parent / f"{self.base_path.stem}_{file_key}.log"
            self.handlers[file_key] = logging.FileHandler(str(file_path), encoding='utf-8')
            
            # Copy formatter from parent
            if self.formatter:
                self.handlers[file_key].setFormatter(self.formatter)
        
        return self.handlers[file_key]
    
    def flush(self):
        """Flush all handlers"""
        for handler in self.handlers.values():
            handler.flush()
    
    def close(self):
        """Close all handlers"""
        for handler in self.handlers.values():
            handler.close()
        super().close()
