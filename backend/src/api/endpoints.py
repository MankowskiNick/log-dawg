"""
FastAPI endpoints for Log Dawg
"""
import uuid
import time
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse
from src.models.schemas import (
    LogDiagnosisRequest,
    LogDiagnosisResponse,
    LogDiagnosisQueuedResponse,
    LogDiagnosisStatusResponse,
    HealthCheckResponse,
    ErrorResponse
)
from src.core.config import config_manager
from src.core.log_parser import LogParser
from src.core.git_manager import GitManager
from src.core.llm_engine import LLMEngine
from src.utils.json_report_writer import JsonReportWriter
from src.utils.markdown_generator import MarkdownGenerator
from src.core.logging import initialize_logging, get_logger, get_log_stats, cleanup_logs
from src import __version__

import asyncio

from src.core.logging import get_logger

# Create router
router = APIRouter()

# Initialize components
log_parser = LogParser()
git_manager = GitManager()
llm_engine = LLMEngine()
json_report_writer = JsonReportWriter()
markdown_generator = MarkdownGenerator()

# Diagnosis status/result store
diagnosis_status_store = {}  # diagnosis_id -> dict with status/result/error

@router.post("/logs/diagnose", response_model=LogDiagnosisQueuedResponse)
async def diagnose_log(request: LogDiagnosisRequest, fastapi_request: Request):
    """
    Queue a log diagnosis request and return a diagnosis_id immediately.
    """
    diagnosis_id = str(uuid.uuid4())
    # Store initial status
    diagnosis_status_store[diagnosis_id] = {
        "status": "pending",
        "diagnosis_id": diagnosis_id,
        "timestamp": datetime.now()
    }
    # Enqueue the request
    await fastapi_request.app.state.diagnosis_queue.put((diagnosis_id, request))
    return LogDiagnosisQueuedResponse(diagnosis_id=diagnosis_id, status="pending")

@router.get("/logs/diagnose/status/{diagnosis_id}", response_model=LogDiagnosisStatusResponse)
async def get_diagnosis_status(diagnosis_id: str):
    """
    Get the status/result of a diagnosis by diagnosis_id.
    """
    entry = diagnosis_status_store.get(diagnosis_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Diagnosis ID not found: {diagnosis_id}")
    return LogDiagnosisStatusResponse(**entry)

async def _diagnosis_background_worker(app):
    """
    Background worker to process queued diagnosis requests.
    """
    logger = get_logger("diagnosis_worker")

    # Only one periodic logger should run, so only start it in the first worker
    if not hasattr(_diagnosis_background_worker, "_periodic_logger_started"):
        async def log_queue_periodically():
            while True:
                await asyncio.sleep(10)
                ids = [item[0] for item in list(app.state.diagnosis_queue._queue)]
                logger.info(f"Diagnosis queue contains {len(ids)} IDs: {ids}")
        asyncio.create_task(log_queue_periodically())
        _diagnosis_background_worker._periodic_logger_started = True

    while True:
        diagnosis_id, request = await app.state.diagnosis_queue.get()
        start_time = time.time()
        logger.info(f"[{diagnosis_id}] Pulled request from queue")
        diagnosis_status_store[diagnosis_id] = {
            "status": "processing",
            "diagnosis_id": diagnosis_id,
            "timestamp": datetime.now()
        }
        try:
            logger.info(f"[{diagnosis_id}] Parsing log data")
            parsed_log = log_parser.parse_log_data(request.log_data)
            # Validate this is an error log
            if not log_parser.is_error_log(parsed_log):
                logger.warning(f"[{diagnosis_id}] Log does not contain error information, skipping")
                diagnosis_status_store[diagnosis_id] = {
                    "status": "failed",
                    "diagnosis_id": diagnosis_id,
                    "timestamp": datetime.now(),
                    "error": "Log does not appear to contain error information"
                }
                continue
            # Step 2: Pull latest git changes if requested
            if request.force_git_pull:
                logger.info(f"[{diagnosis_id}] Pulling latest git changes")
                pull_result = git_manager.pull_latest_changes()
                if not pull_result["success"]:
                    logger.warning(f"[{diagnosis_id}] Git pull failed: {pull_result.get('error')}")
            # Step 3: Get git context
            logger.info(f"[{diagnosis_id}] Gathering git context")
            git_info = git_manager.get_git_info()
            recent_commits = None
            if request.include_git_context:
                recent_commits = git_manager.get_recent_commits()
            logger.info(f"[{diagnosis_id}] Starting LLM diagnosis")
            diagnosis_result = await llm_engine.diagnose_log(
                parsed_log=parsed_log,
                git_info=git_info,
                recent_commits=recent_commits,
                diagnosis_id=diagnosis_id
            )
            logger.info(f"[{diagnosis_id}] LLM diagnosis complete")
            if diagnosis_result is None:
                logger.error(f"[{diagnosis_id}] Diagnosis result is None")
                diagnosis_status_store[diagnosis_id] = {
                    "status": "failed",
                    "diagnosis_id": diagnosis_id,
                    "timestamp": datetime.now(),
                    "error": "Diagnosis result is None"
                }
                continue
            processing_time = time.time() - start_time
            logger.info(f"[{diagnosis_id}] Diagnosis processing time: {processing_time:.2f}s")
            # Use Pydantic's native serialization to maintain type safety
            if hasattr(diagnosis_result, 'model_dump'):
                # Pydantic v2 style
                serialized_diagnosis_result = diagnosis_result.model_dump()
            elif hasattr(diagnosis_result, 'dict'):
                # Pydantic v1 style
                serialized_diagnosis_result = diagnosis_result.dict()
            else:
                # Fallback for non-Pydantic objects
                serialized_diagnosis_result = dict(diagnosis_result) if hasattr(diagnosis_result, '__dict__') else diagnosis_result
            
            logger.info(f"[{diagnosis_id}] Serialized diagnosis result with {len(serialized_diagnosis_result.get('relevant_code_files', []))} relevant files")

            response = {
                "diagnosis_id": diagnosis_id,
                "status": "complete",
                "diagnosis_result": serialized_diagnosis_result,
                "git_info": git_info,
                "processing_time_seconds": processing_time,
                "timestamp": datetime.now(),
                "report_file_path": ""
            }
            diagnosis_status_store[diagnosis_id] = response
            logger.info(f"[{diagnosis_id}] Queued report generation")
            asyncio.create_task(_generate_report_background_status(response, parsed_log))
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logger.error(f"[{diagnosis_id}] Exception during diagnosis: {e}\n{tb}")
            diagnosis_status_store[diagnosis_id] = {
                "status": "failed",
                "diagnosis_id": diagnosis_id,
                "timestamp": datetime.now(),
                "error": f"Internal server error during log diagnosis: {e}\n{tb}"
            }

from src.models.schemas import LogDiagnosisResponse

async def _generate_report_background_status(response, parsed_log):
    """Background task to generate JSON report and update status store"""
    logger = get_logger("diagnosis_worker")
    try:
        logger.info(f"[{response['diagnosis_id']}] Generating JSON report")
        # Convert dict to LogDiagnosisResponse for json_report_writer compatibility
        report_obj = LogDiagnosisResponse(
            diagnosis_id=response["diagnosis_id"],
            diagnosis_result=response["diagnosis_result"],
            git_info=response["git_info"],
            processing_time_seconds=response["processing_time_seconds"],
            timestamp=response["timestamp"],
            report_file_path=response.get("report_file_path", "")
        )
        report_id = json_report_writer.save_report(report_obj, parsed_log)
        response["report_id"] = report_id
        response["report_file_path"] = f"report_{report_id}.json"  # For compatibility
        diagnosis_status_store[response["diagnosis_id"]] = response
        logger.info(f"[{response['diagnosis_id']}] JSON report generated with ID: {report_id}")
    except Exception as e:
        logger.error(f"[{response['diagnosis_id']}] Failed to generate report: {e}")


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint
    """
    try:
        # Validate configuration
        validation_result = config_manager.validate_config()
        
        # Get git status
        git_status = git_manager.get_git_status()
        
        return HealthCheckResponse(
            status="healthy" if validation_result["valid"] else "degraded",
            timestamp=datetime.now(),
            version=__version__,
            git_status=git_status,
            configuration_valid=validation_result["valid"]
        )
        
    except Exception as e:
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            version=__version__,
            git_status={"error": str(e)},
            configuration_valid=False
        )

@router.get("/config/validate")
async def validate_configuration():
    """
    Validate current configuration
    """
    try:
        validation_result = config_manager.validate_config()
        return {
            "valid": validation_result["valid"],
            "errors": validation_result["errors"],
            "warnings": validation_result["warnings"],
            "timestamp": datetime.now()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Configuration validation failed: {e}"
        )

@router.get("/git/status")
async def get_git_status():
    """
    Get current git repository status
    """
    try:
        status = git_manager.get_git_status()
        return {
            "git_status": status,
            "timestamp": datetime.now()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get git status: {e}"
        )

@router.post("/git/pull")
async def trigger_git_pull():
    """
    Manually trigger a git pull operation
    """
    try:
        result = git_manager.pull_latest_changes(force=True)
        return {
            "pull_result": result,
            "timestamp": datetime.now()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Git pull failed: {e}"
        )

@router.get("/reports")
async def list_reports(limit: int = 20):
    """
    List recent diagnosis reports (JSON-first)
    """
    try:
        reports = json_report_writer.list_reports(limit=limit)
        stats = json_report_writer.get_report_stats()
        
        return {
            "reports": reports,
            "stats": stats,
            "timestamp": datetime.now()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list reports: {e}"
        )

@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    """
    Get a specific JSON report by ID
    """
    try:
        report_data = json_report_writer.get_report(report_id)
        
        if report_data is None:
            raise HTTPException(
                status_code=404,
                detail=f"Report not found: {report_id}"
            )
        
        return report_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get report: {e}"
        )

@router.post("/reports/{report_id}/download/markdown")
async def download_report_as_markdown(report_id: str):
    """
    Generate and download a report as markdown
    """
    try:
        # Get the JSON report
        json_report = json_report_writer.get_report(report_id)
        
        if json_report is None:
            raise HTTPException(
                status_code=404,
                detail=f"Report not found: {report_id}"
            )
        
        # Generate markdown from JSON
        markdown_content = markdown_generator.generate_from_json(json_report)
        
        # Create a temporary file-like response
        from fastapi.responses import Response
        
        # Generate filename based on report metadata
        metadata = json_report.get('metadata', {})
        diagnosis_result = json_report.get('diagnosis_result', {})
        title = diagnosis_result.get('title', 'Report').replace(' ', '_').replace('/', '_')
        timestamp = metadata.get('timestamp', '').split('T')[0] if metadata.get('timestamp') else 'unknown'
        filename = f"{title}_{timestamp}_{report_id[:8]}.md"
        
        return Response(
            content=markdown_content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Cache-Control": "no-cache"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate markdown: {e}"
        )

@router.delete("/reports/{report_id}")
async def delete_report(report_id: str):
    """
    Delete a specific report
    """
    try:
        success = json_report_writer.delete_report(report_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Report not found: {report_id}"
            )
        
        return {
            "message": f"Report {report_id} deleted successfully",
            "timestamp": datetime.now()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete report: {e}"
        )

@router.get("/stats")
async def get_system_stats():
    """
    Get system statistics and metrics
    """
    try:
        # Get report stats
        report_stats = json_report_writer.get_report_stats()
        
        # Get git info
        git_info = git_manager.get_git_info()
        
        # Get configuration info
        config_validation = config_manager.validate_config()
        
        return {
            "reports": report_stats,
            "git": {
                "branch": git_info.branch,
                "current_commit": git_info.current_commit[:12],
                "last_pull_time": git_info.last_pull_time,
                "recent_commits_count": len(git_info.recent_commits),
                "changed_files_count": len(git_info.changed_files)
            },
            "configuration": {
                "valid": config_validation["valid"],
                "errors_count": len(config_validation["errors"]),
                "warnings_count": len(config_validation["warnings"])
            },
            "version": __version__,
            "timestamp": datetime.now()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system stats: {e}"
        )

@router.get("/logs/stats")
async def get_logging_stats():
    """
    Get logging system statistics
    """
    try:
        log_stats = get_log_stats()
        return {
            "logging_stats": log_stats,
            "timestamp": datetime.now()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get logging stats: {e}"
        )

@router.post("/logs/cleanup")
async def cleanup_old_logs(retention_days: int = None):
    """
    Clean up old log files based on retention policy
    """
    try:
        retention_days = retention_days or config_manager.config.logging.retention_days
        cleanup_logs(retention_days)
        return {
            "message": f"Log cleanup completed with {retention_days} day retention",
            "retention_days": retention_days,
            "timestamp": datetime.now()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup logs: {e}"
        )

@router.get("/logs/diagnoses")
async def list_diagnosis_logs(limit: int = 20):
    """
    List recent diagnosis logs
    """
    try:
        from pathlib import Path
        
        logs_dir = Path(config_manager.config.logging.log_directory) / 'diagnoses'
        diagnosis_logs = []
        
        if logs_dir.exists():
            # Get all diagnosis directories
            for date_dir in sorted(logs_dir.iterdir(), reverse=True):
                if date_dir.is_dir():
                    for diagnosis_dir in sorted(date_dir.iterdir(), reverse=True):
                        if diagnosis_dir.is_dir() and diagnosis_dir.name.startswith('diagnosis-'):
                            diagnosis_id = diagnosis_dir.name.replace('diagnosis-', '')
                            
                            # Get log files in this diagnosis
                            log_files = list(diagnosis_dir.glob('*.log'))
                            total_size = sum(f.stat().st_size for f in log_files)
                            
                            diagnosis_logs.append({
                                'diagnosis_id': diagnosis_id,
                                'date': date_dir.name,
                                'log_files': [f.name for f in log_files],
                                'total_size_bytes': total_size,
                                'created': datetime.fromtimestamp(diagnosis_dir.stat().st_ctime),
                                'modified': datetime.fromtimestamp(diagnosis_dir.stat().st_mtime)
                            })
                            
                            if len(diagnosis_logs) >= limit:
                                break
                if len(diagnosis_logs) >= limit:
                    break
        
        return {
            "diagnosis_logs": diagnosis_logs,
            "total_count": len(diagnosis_logs),
            "timestamp": datetime.now()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list diagnosis logs: {e}"
        )

@router.get("/logs/diagnoses/{diagnosis_id}")
async def get_diagnosis_logs(diagnosis_id: str):
    """
    Get all log files for a specific diagnosis
    """
    try:
        from pathlib import Path
        
        logs_dir = Path(config_manager.config.logging.log_directory) / 'diagnoses'
        diagnosis_logs = {}
        
        # Search for the diagnosis across all date directories
        for date_dir in logs_dir.iterdir():
            if date_dir.is_dir():
                diagnosis_dir = date_dir / f'diagnosis-{diagnosis_id}'
                if diagnosis_dir.exists():
                    # Read all log files
                    for log_file in diagnosis_dir.glob('*.log'):
                        try:
                            with open(log_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                            diagnosis_logs[log_file.name] = {
                                'content': content,
                                'size_bytes': log_file.stat().st_size,
                                'modified': datetime.fromtimestamp(log_file.stat().st_mtime)
                            }
                        except Exception as e:
                            diagnosis_logs[log_file.name] = {
                                'error': f"Failed to read file: {e}",
                                'size_bytes': log_file.stat().st_size,
                                'modified': datetime.fromtimestamp(log_file.stat().st_mtime)
                            }
                    break
        
        if not diagnosis_logs:
            raise HTTPException(
                status_code=404,
                detail=f"Diagnosis logs not found for ID: {diagnosis_id}"
            )
        
        return {
            "diagnosis_id": diagnosis_id,
            "log_files": diagnosis_logs,
            "timestamp": datetime.now()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get diagnosis logs: {e}"
        )

# Note: Exception handlers are added to the main FastAPI app in main.py
