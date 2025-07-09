"""
Main FastAPI application for Log Dawg
"""
import logging
import sys
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.api.endpoints import router
from src.core.config import config_manager
from src.core.logging import initialize_logging, get_logger
from src import __version__

# Initialize the logging system
logging_config = {
    'level': config_manager.config.logging.level,
    'log_directory': config_manager.config.logging.log_directory,
    'console_logging': config_manager.config.logging.console_logging,
    'file_logging': config_manager.config.logging.file_logging,
    'structured_format': config_manager.config.logging.structured_format,
    'max_log_size_mb': config_manager.config.logging.max_log_size_mb,
    'retention_days': config_manager.config.logging.retention_days
}

initialize_logging(logging_config)
logger = get_logger('api')

from src.api.endpoints import _diagnosis_background_worker

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info(f"Starting Log Dawg v{__version__}")

    # Validate configuration on startup
    validation_result = config_manager.validate_config()
    if not validation_result["valid"]:
        logger.error("Configuration validation failed:")
        for error in validation_result["errors"]:
            logger.error(f"  - {error}")
        sys.exit(1)

    # Log warnings
    for warning in validation_result["warnings"]:
        logger.warning(warning)

    # Create diagnosis queue and store in app.state
    import asyncio
    app.state.diagnosis_queue = asyncio.Queue()
    worker_count = getattr(config_manager.config.server, "diagnosis_worker_count", 4)
    for _ in range(worker_count):
        asyncio.create_task(_diagnosis_background_worker(app))

    logger.info("Log Dawg started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Log Dawg")

# Create FastAPI application
app = FastAPI(
    title="Log Dawg",
    description="LLM-powered log diagnosis agent with git context",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    start_time = time.time()
    
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.3f}s")
    
    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred",
            "path": str(request.url)
        }
    )

# Include API router
app.include_router(router, prefix="/api/v1")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with basic information"""
    return {
        "name": "Log Dawg",
        "version": __version__,
        "description": "LLM-powered log diagnosis agent with git context",
        "docs_url": "/docs",
        "health_check": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    
    config = config_manager.config
    
    uvicorn.run(
        "src.main:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
        workers=config.server.http_workers,
        log_level=config_manager.settings.log_level.lower()
    )
