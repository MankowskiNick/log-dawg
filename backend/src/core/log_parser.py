"""
Log parsing module for handling various AWS log formats
"""
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from src.models.schemas import ParsedLogEntry, LogData

class LogParser:
    """Parses various log formats from AWS and other sources"""
    
    def __init__(self):
        self.error_patterns = [
            r'ERROR',
            r'FATAL',
            r'CRITICAL',
            r'Exception',
            r'Traceback',
            r'Error:',
            r'Failed',
            r'Failure',
            r'Stack trace',
            r'at\s+[\w\.]+\([^)]+\)',  # Java/Scala stack traces
            r'File\s+"[^"]+",\s+line\s+\d+',  # Python stack traces
        ]
        
        self.timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?',  # ISO format
            r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',  # Standard format
            r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}',  # US format
            r'\w{3} \d{1,2} \d{2}:\d{2}:\d{2}',  # Syslog format
        ]
    
    def parse_log_data(self, log_data: LogData) -> ParsedLogEntry:
        """Parse log data into a structured format"""
        if isinstance(log_data.content, dict):
            return self._parse_json_log(log_data)
        else:
            return self._parse_text_log(log_data)
    
    def _parse_json_log(self, log_data: LogData) -> ParsedLogEntry:
        """Parse JSON-formatted log data"""
        content = log_data.content
        
        # Extract common fields from JSON structure
        timestamp = self._extract_timestamp_from_json(content)
        if not timestamp and log_data.timestamp:
            timestamp = log_data.timestamp
        
        level = self._extract_log_level_from_json(content)
        message = self._extract_message_from_json(content)
        source = log_data.source or self._extract_source_from_json(content)
        service_name = self._extract_service_name_from_json(content)
        stack_trace = self._extract_stack_trace_from_json(content)
        
        # Extract error messages
        extracted_errors = self._extract_errors_from_text(json.dumps(content))
        
        return ParsedLogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            source=source,
            stack_trace=stack_trace,
            service_name=service_name,
            raw_content=content,
            extracted_errors=extracted_errors
        )
    
    def _parse_text_log(self, log_data: LogData) -> ParsedLogEntry:
        """Parse plain text log data"""
        content = str(log_data.content)
        
        # Extract timestamp
        timestamp = self._extract_timestamp_from_text(content)
        if not timestamp and log_data.timestamp:
            timestamp = log_data.timestamp
        
        # Extract log level
        level = self._extract_log_level_from_text(content)
        
        # Use entire content as message for text logs
        message = content.strip()
        
        # Extract stack trace if present
        stack_trace = self._extract_stack_trace_from_text(content)
        
        # Extract errors
        extracted_errors = self._extract_errors_from_text(content)
        
        return ParsedLogEntry(
            timestamp=timestamp,
            level=level,
            message=message,
            source=log_data.source,
            stack_trace=stack_trace,
            service_name=None,
            raw_content=content,
            extracted_errors=extracted_errors
        )
    
    def _extract_timestamp_from_json(self, content: Dict[str, Any]) -> Optional[datetime]:
        """Extract timestamp from JSON log content"""
        timestamp_fields = ['timestamp', 'time', '@timestamp', 'eventTime', 'date']
        
        for field in timestamp_fields:
            if field in content:
                try:
                    ts = content[field]
                    if isinstance(ts, str):
                        return self._parse_timestamp_string(ts)
                    elif isinstance(ts, (int, float)):
                        return datetime.fromtimestamp(ts)
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _extract_timestamp_from_text(self, content: str) -> Optional[datetime]:
        """Extract timestamp from text log content"""
        for pattern in self.timestamp_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    return self._parse_timestamp_string(match.group())
                except ValueError:
                    continue
        return None
    
    def _parse_timestamp_string(self, ts_str: str) -> datetime:
        """Parse timestamp string into datetime object"""
        # Try various timestamp formats
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%m/%d/%Y %H:%M:%S',
            '%b %d %H:%M:%S'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Unable to parse timestamp: {ts_str}")
    
    def _extract_log_level_from_json(self, content: Dict[str, Any]) -> str:
        """Extract log level from JSON content"""
        level_fields = ['level', 'severity', 'priority', 'logLevel']
        
        for field in level_fields:
            if field in content:
                level = str(content[field]).upper()
                if level in ['DEBUG', 'INFO', 'WARN', 'WARNING', 'ERROR', 'FATAL', 'CRITICAL']:
                    return level
        
        # Check if message contains error indicators
        message = self._extract_message_from_json(content)
        if any(pattern.upper() in message.upper() for pattern in ['ERROR', 'FATAL', 'CRITICAL']):
            return 'ERROR'
        
        return 'INFO'
    
    def _extract_log_level_from_text(self, content: str) -> str:
        """Extract log level from text content"""
        levels = ['FATAL', 'CRITICAL', 'ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG']
        
        for level in levels:
            if re.search(rf'\b{level}\b', content, re.IGNORECASE):
                return level.upper()
        
        return 'INFO'
    
    def _extract_message_from_json(self, content: Dict[str, Any]) -> str:
        """Extract main message from JSON content"""
        message_fields = ['message', 'msg', 'text', 'description', 'error']
        
        for field in message_fields:
            if field in content:
                return str(content[field])
        
        # If no specific message field, return JSON string
        return json.dumps(content)
    
    def _extract_source_from_json(self, content: Dict[str, Any]) -> Optional[str]:
        """Extract source information from JSON content"""
        source_fields = ['source', 'logger', 'loggerName', 'component']
        
        for field in source_fields:
            if field in content:
                return str(content[field])
        
        return None
    
    def _extract_service_name_from_json(self, content: Dict[str, Any]) -> Optional[str]:
        """Extract service name from JSON content"""
        service_fields = ['service', 'serviceName', 'application', 'app']
        
        for field in service_fields:
            if field in content:
                return str(content[field])
        
        return None
    
    def _extract_stack_trace_from_json(self, content: Dict[str, Any]) -> Optional[str]:
        """Extract stack trace from JSON content"""
        stack_fields = ['stackTrace', 'stack', 'trace', 'exception']
        
        for field in stack_fields:
            if field in content:
                return str(content[field])
        
        return None
    
    def _extract_stack_trace_from_text(self, content: str) -> Optional[str]:
        """Extract stack trace from text content"""
        # Look for common stack trace patterns
        patterns = [
            r'Traceback \(most recent call last\):.*?(?=\n\S|\Z)',
            r'Stack trace:.*?(?=\n\S|\Z)',
            r'Exception in thread.*?(?=\n\S|\Z)',
            r'at\s+[\w\.\$]+\([^)]*\)(?:\s*\n\s*at\s+[\w\.\$]+\([^)]*\))*'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
            if match:
                return match.group().strip()
        
        return None
    
    def _extract_errors_from_text(self, content: str) -> List[str]:
        """Extract error messages from text using regex patterns"""
        errors = []
        
        for pattern in self.error_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                # Get the line containing the error
                start = content.rfind('\n', 0, match.start()) + 1
                end = content.find('\n', match.end())
                if end == -1:
                    end = len(content)
                
                error_line = content[start:end].strip()
                if error_line and error_line not in errors:
                    errors.append(error_line)
        
        return errors
    
    def is_error_log(self, parsed_log: ParsedLogEntry) -> bool:
        """Determine if the parsed log represents an error"""
        error_levels = ['ERROR', 'FATAL', 'CRITICAL']
        
        if parsed_log.level in error_levels:
            return True
        
        if parsed_log.extracted_errors:
            return True
        
        if parsed_log.stack_trace:
            return True
        
        return False
