"""
Error handler service for storing errors in database and logging to files.
"""
import logging
import traceback
import json
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from .models import ErrorLog
from .database import SessionLocal
import uuid

# Set up file-based logging
file_logger = logging.getLogger("error_file_logger")
file_logger.setLevel(logging.ERROR)

# Create logs directory if it doesn't exist
import os
log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(log_dir, exist_ok=True)

# File handler for error logs
file_handler = logging.FileHandler(
    os.path.join(log_dir, "errors.log"),
    encoding="utf-8"
)
file_handler.setLevel(logging.ERROR)
file_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)
file_logger.addHandler(file_handler)

# Also log INFO and above to a general log file
general_logger = logging.getLogger("general_file_logger")
general_logger.setLevel(logging.INFO)
general_handler = logging.FileHandler(
    os.path.join(log_dir, "app.log"),
    encoding="utf-8"
)
general_handler.setLevel(logging.INFO)
general_handler.setFormatter(file_formatter)
general_logger.addHandler(general_handler)


def store_error_in_db(
    error_type: str,
    error_message: str,
    error_details: Dict[str, Any],
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    client_ip: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    request_body: Optional[Dict[str, Any]] = None,
    stack_trace: Optional[str] = None,
    db: Optional[Session] = None
) -> ErrorLog:
    """
    Store an error in the database with JSONB details.
    
    Args:
        error_type: Type/category of error (e.g., "POST_ERROR", "PROCESSING_ERROR")
        error_message: Human-readable error message
        error_details: Dictionary with full error details (will be stored as JSONB)
        endpoint: API endpoint where error occurred
        method: HTTP method
        client_ip: Client IP address
        user_id: User ID if authenticated
        request_body: Request body if available
        stack_trace: Full stack trace
        db: Database session (if None, creates a new one)
    
    Returns:
        ErrorLog instance
    """
    should_close_db = False
    if db is None:
        db = SessionLocal()
        should_close_db = True
    
    try:
        error_log = ErrorLog(
            error_type=error_type,
            error_message=error_message,
            error_details=error_details,
            endpoint=endpoint,
            method=method,
            client_ip=client_ip,
            user_id=user_id,
            request_body=request_body,
            stack_trace=stack_trace
        )
        db.add(error_log)
        db.commit()
        db.refresh(error_log)
        return error_log
    except Exception as e:
        db.rollback()
        # Log to file if DB storage fails
        file_logger.error(
            f"Failed to store error in database: {str(e)}\n"
            f"Original error: {error_type} - {error_message}\n"
            f"Details: {json.dumps(error_details, indent=2)}"
        )
        raise
    finally:
        if should_close_db:
            db.close()


def log_and_store_error(
    error: Exception,
    error_type: str,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    client_ip: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    request_body: Optional[Dict[str, Any]] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> Optional[ErrorLog]:
    """
    Log error to file and store in database.
    
    Args:
        error: Exception object
        error_type: Type/category of error
        endpoint: API endpoint where error occurred
        method: HTTP method
        client_ip: Client IP address
        user_id: User ID if authenticated
        request_body: Request body if available
        additional_context: Additional context to include in error_details
    
    Returns:
        ErrorLog instance if successful, None otherwise
    """
    error_message = str(error)
    stack_trace = traceback.format_exc()
    
    # Prepare error details as JSONB
    error_details = {
        "exception_type": type(error).__name__,
        "exception_module": type(error).__module__,
        "error_message": error_message,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    if additional_context:
        error_details.update(additional_context)
    
    # Log to file
    log_message = (
        f"Error Type: {error_type}\n"
        f"Endpoint: {endpoint or 'N/A'}\n"
        f"Method: {method or 'N/A'}\n"
        f"Client IP: {client_ip or 'N/A'}\n"
        f"User ID: {user_id or 'N/A'}\n"
        f"Error: {error_message}\n"
        f"Stack Trace:\n{stack_trace}"
    )
    
    if request_body:
        log_message += f"\nRequest Body: {json.dumps(request_body, indent=2, default=str)}"
    
    file_logger.error(log_message)
    
    # Store in database
    try:
        return store_error_in_db(
            error_type=error_type,
            error_message=error_message,
            error_details=error_details,
            endpoint=endpoint,
            method=method,
            client_ip=client_ip,
            user_id=user_id,
            request_body=request_body,
            stack_trace=stack_trace
        )
    except Exception as db_error:
        # If DB storage fails, at least we have it in the log file
        file_logger.error(f"Failed to store error in database: {str(db_error)}")
        return None

