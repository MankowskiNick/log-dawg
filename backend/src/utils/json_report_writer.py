"""
JSON report writer for log diagnosis results
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from src.models.schemas import LogDiagnosisResponse, DiagnosisResult, GitInfo, ParsedLogEntry
from src.core.config import config_manager

class JsonReportWriter:
    """Generates and manages JSON reports for log diagnosis results"""
    
    def __init__(self):
        self.config = config_manager.config
        self.reports_dir = Path(self.config.reports.output_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def save_report(
        self, 
        diagnosis_response: LogDiagnosisResponse,
        parsed_log: ParsedLogEntry
    ) -> str:
        """Save a diagnosis report as JSON and return the report ID"""
        
        # Generate unique report ID
        report_id = str(uuid.uuid4())
        
        # Create JSON report structure
        json_report = self._build_json_report(diagnosis_response, parsed_log, report_id)
        
        # Generate filename with report ID
        filename = f"report_{report_id}.json"
        report_path = self.reports_dir / filename
        
        # Write JSON to file
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False, default=str)
        
        # Clean up old reports if needed
        self._cleanup_old_reports()
        
        return report_id
    
    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific report by ID"""
        filename = f"report_{report_id}.json"
        report_path = self.reports_dir / filename
        
        if not report_path.exists():
            return None
        
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error reading report {report_id}: {e}")
            return None
    
    def list_reports(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent reports with metadata"""
        report_files = []
        
        for file_path in self.reports_dir.glob("report_*.json"):
            if file_path.is_file():
                try:
                    # Extract report ID from filename
                    report_id = file_path.stem.replace('report_', '')
                    
                    # Get file stats
                    stat = file_path.stat()
                    
                    # Load report for metadata
                    with open(file_path, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)
                    
                    # Extract key metadata
                    metadata = report_data.get('metadata', {})
                    diagnosis_result = report_data.get('diagnosis_result', {})
                    
                    report_info = {
                        "report_id": report_id,
                        "filename": file_path.name,  # Keep for compatibility
                        "path": str(file_path),
                        "size_bytes": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_ctime),
                        "modified": datetime.fromtimestamp(stat.st_mtime),
                        "display_title": diagnosis_result.get('title', 'Unknown Error'),
                        "error_type": diagnosis_result.get('error_type', 'Unknown'),
                        "confidence_score": diagnosis_result.get('confidence_score', 0.0),
                        "processing_time": metadata.get('processing_time_seconds', 0.0),
                        "summary_preview": self._generate_summary_preview(
                            diagnosis_result.get('summary', '')
                        ),
                        "diagnosis_id": metadata.get('diagnosis_id'),
                        "timestamp": metadata.get('timestamp')
                    }
                    
                    report_files.append(report_info)
                    
                except Exception as e:
                    print(f"Error processing report file {file_path.name}: {e}")
                    continue
        
        # Sort by creation time (newest first)
        report_files.sort(key=lambda x: x["created"], reverse=True)
        
        return report_files[:limit]
    
    def delete_report(self, report_id: str) -> bool:
        """Delete a specific report"""
        filename = f"report_{report_id}.json"
        report_path = self.reports_dir / filename
        
        if not report_path.exists():
            return False
        
        try:
            report_path.unlink()
            return True
        except Exception as e:
            print(f"Error deleting report {report_id}: {e}")
            return False
    
    def get_report_stats(self) -> Dict[str, Any]:
        """Get statistics about reports"""
        report_files = list(self.reports_dir.glob("report_*.json"))
        
        if not report_files:
            return {
                "total_reports": 0,
                "total_size_mb": 0,
                "oldest_report": None,
                "newest_report": None,
                "reports_today": 0,
                "average_confidence_score": 0
            }
        
        total_size = sum(f.stat().st_size for f in report_files)
        creation_times = [f.stat().st_ctime for f in report_files]
        
        # Calculate reports today and average confidence
        today = datetime.now().date()
        reports_today = 0
        confidence_scores = []
        
        for report_file in report_files:
            # Check if report was created today
            file_date = datetime.fromtimestamp(report_file.stat().st_ctime).date()
            if file_date == today:
                reports_today += 1
            
            # Try to get confidence score
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                    confidence = report_data.get('diagnosis_result', {}).get('confidence_score')
                    if confidence is not None:
                        confidence_scores.append(confidence)
            except Exception:
                continue
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        return {
            "total_reports": len(report_files),
            "total_size_mb": total_size / (1024 * 1024),
            "oldest_report": datetime.fromtimestamp(min(creation_times)),
            "newest_report": datetime.fromtimestamp(max(creation_times)),
            "reports_today": reports_today,
            "average_confidence_score": round(avg_confidence * 100, 1)
        }
    
    def _build_json_report(
        self, 
        diagnosis_response: LogDiagnosisResponse,
        parsed_log: ParsedLogEntry,
        report_id: str
    ) -> Dict[str, Any]:
        """Build the complete JSON report structure"""
        
        return {
            "report_id": report_id,
            "version": "2.0",  # JSON-first version
            "metadata": {
                "diagnosis_id": diagnosis_response.diagnosis_id,
                "timestamp": diagnosis_response.timestamp.isoformat(),
                "processing_time_seconds": diagnosis_response.processing_time_seconds,
                "generated_at": datetime.now().isoformat(),
                "format": "json"
            },
            "diagnosis_result": {
                "title": diagnosis_response.diagnosis_result.title,
                "error_type": diagnosis_response.diagnosis_result.error_type,
                "summary": diagnosis_response.diagnosis_result.summary,
                "root_cause": diagnosis_response.diagnosis_result.root_cause,
                "error_analysis": diagnosis_response.diagnosis_result.error_analysis,
                "recommendations": diagnosis_response.diagnosis_result.recommendations,
                "confidence_score": diagnosis_response.diagnosis_result.confidence_score,
                "relevant_code_files": [
                    {
                        "file_path": f.file_path,
                        "size_kb": f.size_kb,
                        "snippets": [
                            {
                                "start_line": snippet.start_line,
                                "end_line": snippet.end_line,
                                "content": snippet.content
                            }
                            for snippet in (f.snippets or [])
                        ],
                        "relevance_score": f.relevance_score,
                        "selection_reason": f.selection_reason
                    }
                    for f in (diagnosis_response.diagnosis_result.relevant_code_files or [])
                ]
            },
            "git_info": {
                "branch": diagnosis_response.git_info.branch,
                "current_commit": diagnosis_response.git_info.current_commit,
                "last_pull_time": diagnosis_response.git_info.last_pull_time.isoformat(),
                "recent_commits": diagnosis_response.git_info.recent_commits,
                "changed_files": diagnosis_response.git_info.changed_files
            },
            "parsed_log": {
                "timestamp": parsed_log.timestamp.isoformat() if parsed_log.timestamp else None,
                "level": parsed_log.level,
                "message": parsed_log.message,
                "source": parsed_log.source,
                "service_name": parsed_log.service_name,
                "stack_trace": parsed_log.stack_trace,
                "extracted_errors": parsed_log.extracted_errors,
                "raw_content": parsed_log.raw_content
            }
        }
    
    def _generate_summary_preview(self, summary: str) -> str:
        """Generate a short preview from the summary"""
        if not summary:
            return "No summary available"
        
        # Get first 2 sentences
        import re
        sentences = re.split(r'[.!?]+', summary.strip())
        preview_sentences = []
        
        for sentence in sentences[:2]:
            sentence = sentence.strip()
            if sentence:
                preview_sentences.append(sentence)
        
        preview = '. '.join(preview_sentences)
        if preview and not preview.endswith('.'):
            preview += '.'
        
        # Limit length
        if len(preview) > 200:
            preview = preview[:197] + "..."
        
        return preview if preview else "No preview available"
    
    def _cleanup_old_reports(self):
        """Clean up old reports if exceeding max limit"""
        max_reports = self.config.reports.max_reports
        
        if max_reports <= 0:
            return
        
        # Get all report files sorted by modification time
        report_files = []
        for file_path in self.reports_dir.glob("report_*.json"):
            if file_path.is_file():
                report_files.append((file_path.stat().st_mtime, file_path))
        
        # Sort by modification time (newest first)
        report_files.sort(reverse=True)
        
        # Remove excess files
        if len(report_files) > max_reports:
            files_to_remove = report_files[max_reports:]
            for _, file_path in files_to_remove:
                try:
                    file_path.unlink()
                    print(f"Removed old report: {file_path.name}")
                except Exception as e:
                    print(f"Failed to remove old report {file_path.name}: {e}")
